"""Round-robin LLM dispatcher across permanently-free-tier providers.

Scoring rotates across 6 providers (Gemini 2.5 Flash-Lite, Groq Llama 3.3 70B
Versatile, Cerebras gpt-oss-120b, Mistral Large, NVIDIA NIM Llama 3.3 70B,
OpenRouter Qwen3-Next 80B free). Tailor summaries always use Groq Llama 3.1 8B
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
GROQ_SCORING_MODEL = "llama-3.3-70b-versatile"
GROQ_FAST_MODEL = "llama-3.1-8b-instant"
CEREBRAS_MODEL = "gpt-oss-120b"
MISTRAL_MODEL = "mistral-large-latest"
NVIDIA_MODEL = "meta/llama-3.3-70b-instruct"
OPENROUTER_MODEL = "qwen/qwen3-next-80b-a3b-instruct:free"

DEBUG = os.environ.get("LLM_DEBUG") == "1"

PROVIDER_DAILY_CAP = {
    "gemini": 14000,
    "groq": 1000,
    "cerebras": 14000,
    "mistral": 100000,
    "nvidia": 14000,
    "openrouter": 50,
    "groq_fast": 14000,
}
PROVIDER_ENV_KEYS = {
    "gemini": "GEMINI_API_KEY",
    "groq": "GROQ_API_KEY",
    "cerebras": "CEREBRAS_API_KEY",
    "mistral": "MISTRAL_API_KEY",
    "nvidia": "NVIDIA_API_KEY",
    "openrouter": "OPENROUTER_API_KEY",
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


def _mistral():
    with _client_lock:
        if "mistral" not in _clients:
            _clients["mistral"] = OpenAI(
                api_key=os.environ["MISTRAL_API_KEY"],
                base_url="https://api.mistral.ai/v1",
            )
    return _clients["mistral"]


def _nvidia():
    with _client_lock:
        if "nvidia" not in _clients:
            _clients["nvidia"] = OpenAI(
                api_key=os.environ["NVIDIA_API_KEY"],
                base_url="https://integrate.api.nvidia.com/v1",
            )
    return _clients["nvidia"]


def _openrouter():
    with _client_lock:
        if "openrouter" not in _clients:
            _clients["openrouter"] = OpenAI(
                api_key=os.environ["OPENROUTER_API_KEY"],
                base_url="https://openrouter.ai/api/v1",
            )
    return _clients["openrouter"]


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


def _call_groq_scoring(prompt: str, want_json: bool) -> str:
    return _call_openai_compat(_groq(), GROQ_SCORING_MODEL, prompt, want_json)


def _call_cerebras(prompt: str, want_json: bool) -> str:
    return _call_openai_compat(_cerebras(), CEREBRAS_MODEL, prompt, want_json)


def _call_mistral(prompt: str, want_json: bool) -> str:
    return _call_openai_compat(_mistral(), MISTRAL_MODEL, prompt, want_json)


def _call_nvidia(prompt: str, want_json: bool) -> str:
    return _call_openai_compat(_nvidia(), NVIDIA_MODEL, prompt, want_json)


def _call_openrouter(prompt: str, want_json: bool) -> str:
    return _call_openai_compat(_openrouter(), OPENROUTER_MODEL, prompt, want_json)


def _call_groq_fast(prompt: str, want_json: bool) -> str:
    return _call_openai_compat(_groq(), GROQ_FAST_MODEL, prompt, want_json)


SCORING_PROVIDERS = [
    ("gemini", _call_gemini),
    ("groq", _call_groq_scoring),
    ("cerebras", _call_cerebras),
    ("mistral", _call_mistral),
    ("nvidia", _call_nvidia),
    ("openrouter", _call_openrouter),
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
