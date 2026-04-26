"""Round-robin LLM dispatcher across free-tier providers.

Scoring rotates across 4 providers (Gemini 2.5 Flash-Lite, Hyperbolic 70B,
SambaNova 70B, Cerebras 70B). Tailor summaries always use Groq Llama 3.1 8B
via call_llm_fast.

Tracks per-provider daily call counts (reset at UTC midnight) and 60s
cooling-off windows so we don't re-hit a provider that just told us it's
throttled. On a full sweep where every scoring provider is throttled or
exhausted, sleeps 30s and re-sweeps once before raising.
"""
import itertools
import os
import threading
import time
from datetime import date, datetime

from google import genai
from google.genai import types as genai_types
from groq import Groq
from openai import OpenAI

GEMINI_MODEL = "gemini-2.5-flash-lite"
HYPERBOLIC_MODEL = "meta-llama/Llama-3.3-70B-Instruct"
SAMBANOVA_MODEL = "Meta-Llama-3.3-70B-Instruct"
CEREBRAS_MODEL = "llama-3.3-70b"
GROQ_FAST_MODEL = "llama-3.1-8b-instant"

DEBUG = os.environ.get("LLM_DEBUG") == "1"

PROVIDER_DAILY_CAP = {
    "gemini": 14000,
    "hyperbolic": 5000,
    "sambanova": 14000,
    "cerebras": 14000,
    "groq_fast": 14000,
}
PROVIDER_ENV_KEYS = {
    "gemini": "GEMINI_API_KEY",
    "hyperbolic": "HYPERBOLIC_API_KEY",
    "sambanova": "SAMBANOVA_API_KEY",
    "cerebras": "CEREBRAS_API_KEY",
    "groq_fast": "GROQ_API_KEY",
}
COOLDOWN_SECONDS = 60
SWEEP_BACKOFF_SECONDS = 30

_clients: dict = {}
_client_lock = threading.Lock()

_daily_counts: dict[str, int] = {n: 0 for n in PROVIDER_DAILY_CAP}
_daily_date: date = datetime.utcnow().date()
_cooling_until: dict[str, float] = {n: 0.0 for n in PROVIDER_DAILY_CAP}
_quota_lock = threading.Lock()


def _gemini():
    with _client_lock:
        if "gemini" not in _clients:
            _clients["gemini"] = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
    return _clients["gemini"]


def _groq():
    with _client_lock:
        if "groq" not in _clients:
            _clients["groq"] = Groq(api_key=os.environ["GROQ_API_KEY"])
    return _clients["groq"]


def _cerebras():
    with _client_lock:
        if "cerebras" not in _clients:
            _clients["cerebras"] = OpenAI(
                api_key=os.environ["CEREBRAS_API_KEY"],
                base_url="https://api.cerebras.ai/v1",
            )
    return _clients["cerebras"]


def _hyperbolic():
    with _client_lock:
        if "hyperbolic" not in _clients:
            _clients["hyperbolic"] = OpenAI(
                api_key=os.environ["HYPERBOLIC_API_KEY"],
                base_url="https://api.hyperbolic.xyz/v1",
            )
    return _clients["hyperbolic"]


def _sambanova():
    with _client_lock:
        if "sambanova" not in _clients:
            _clients["sambanova"] = OpenAI(
                api_key=os.environ["SAMBANOVA_API_KEY"],
                base_url="https://api.sambanova.ai/v1",
            )
    return _clients["sambanova"]


def _call_gemini(prompt: str, want_json: bool) -> str:
    cfg = (
        genai_types.GenerateContentConfig(response_mime_type="application/json")
        if want_json
        else None
    )
    resp = _gemini().models.generate_content(
        model=GEMINI_MODEL, contents=prompt, config=cfg
    )
    return resp.text


def _call_openai_compat(client, model: str, prompt: str, want_json: bool) -> str:
    kw = {"response_format": {"type": "json_object"}} if want_json else {}
    r = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        **kw,
    )
    return r.choices[0].message.content


def _call_hyperbolic(prompt: str, want_json: bool) -> str:
    return _call_openai_compat(_hyperbolic(), HYPERBOLIC_MODEL, prompt, want_json)


def _call_sambanova(prompt: str, want_json: bool) -> str:
    return _call_openai_compat(_sambanova(), SAMBANOVA_MODEL, prompt, want_json)


def _call_cerebras(prompt: str, want_json: bool) -> str:
    return _call_openai_compat(_cerebras(), CEREBRAS_MODEL, prompt, want_json)


def _call_groq_fast(prompt: str, want_json: bool) -> str:
    return _call_openai_compat(_groq(), GROQ_FAST_MODEL, prompt, want_json)


SCORING_PROVIDERS = [
    ("gemini", _call_gemini),
    ("hyperbolic", _call_hyperbolic),
    ("sambanova", _call_sambanova),
    ("cerebras", _call_cerebras),
]
_rotator = itertools.cycle(range(len(SCORING_PROVIDERS)))
_rot_lock = threading.Lock()


def _next_start_idx() -> int:
    with _rot_lock:
        return next(_rotator)


def _is_rate_error(e: Exception) -> bool:
    msg = str(e).lower()
    return any(
        t in msg
        for t in ("429", "quota", "resource_exhausted", "rate limit", "rate_limit")
    )


def _maybe_reset_daily():
    """Caller holds _quota_lock."""
    global _daily_date
    today = datetime.utcnow().date()
    if today != _daily_date:
        _daily_date = today
        for name in _daily_counts:
            _daily_counts[name] = 0


def _is_eligible(name: str, now: float) -> bool:
    """Caller holds _quota_lock."""
    if not os.environ.get(PROVIDER_ENV_KEYS[name]):
        return False
    _maybe_reset_daily()
    if _daily_counts[name] >= PROVIDER_DAILY_CAP[name]:
        return False
    if now < _cooling_until[name]:
        return False
    return True


def _mark_used(name: str):
    with _quota_lock:
        _maybe_reset_daily()
        _daily_counts[name] += 1


def _mark_throttled(name: str):
    with _quota_lock:
        _cooling_until[name] = time.time() + COOLDOWN_SECONDS


def call_llm(prompt: str, want_json: bool = True) -> str:
    """Round-robin across scoring providers; on full sweep miss, sleep + re-sweep once."""
    last_err: Exception | None = None
    for sweep in range(2):
        start_idx = _next_start_idx()
        for offset in range(len(SCORING_PROVIDERS)):
            name, fn = SCORING_PROVIDERS[(start_idx + offset) % len(SCORING_PROVIDERS)]
            with _quota_lock:
                if not _is_eligible(name, time.time()):
                    continue
            try:
                result = fn(prompt, want_json)
                _mark_used(name)
                if DEBUG:
                    print(f"    [llm] {name} served")
                return result
            except Exception as e:
                last_err = e
                if DEBUG:
                    print(f"    [llm] {name} failed: {str(e)[:120]}")
                if _is_rate_error(e):
                    _mark_throttled(name)
        if sweep == 0:
            if DEBUG:
                print(f"    [llm] sweep miss, sleeping {SWEEP_BACKOFF_SECONDS}s")
            time.sleep(SWEEP_BACKOFF_SECONDS)
    raise RuntimeError(f"all providers failed: {last_err}")


def call_llm_fast(prompt: str, want_json: bool = False) -> str:
    """Tailor's fast lane: always Groq Llama 3.1 8B (high daily quota, lower judgment quality)."""
    last_err: Exception | None = None
    for attempt in range(3):
        with _quota_lock:
            eligible = _is_eligible("groq_fast", time.time())
        if not eligible:
            time.sleep(SWEEP_BACKOFF_SECONDS)
            continue
        try:
            result = _call_groq_fast(prompt, want_json)
            _mark_used("groq_fast")
            if DEBUG:
                print("    [llm-fast] groq_fast served")
            return result
        except Exception as e:
            last_err = e
            if DEBUG:
                print(f"    [llm-fast] groq_fast failed: {str(e)[:120]}")
            if _is_rate_error(e):
                _mark_throttled("groq_fast")
                time.sleep(SWEEP_BACKOFF_SECONDS)
            else:
                time.sleep(2 ** attempt)
    raise RuntimeError(f"groq_fast failed: {last_err}")
