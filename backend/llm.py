"""Round-robin LLM dispatcher across Gemini, Groq, and Cerebras free tiers.

Each worker thread gets a different start provider; on 429/quota errors
the call rotates to the next provider rather than burning retries on a
throttled one.
"""
import itertools
import os
import threading
import time

from google import genai
from google.genai import types as genai_types
from groq import Groq
from openai import OpenAI

GEMINI_MODEL = "gemini-2.0-flash"
GROQ_MODEL = "llama-3.3-70b-versatile"
CEREBRAS_MODEL = "llama-3.3-70b"

DEBUG = os.environ.get("LLM_DEBUG") == "1"

_clients: dict = {}
_client_lock = threading.Lock()


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


def _call_groq(prompt: str, want_json: bool) -> str:
    kw = {"response_format": {"type": "json_object"}} if want_json else {}
    r = _groq().chat.completions.create(
        model=GROQ_MODEL,
        messages=[{"role": "user", "content": prompt}],
        **kw,
    )
    return r.choices[0].message.content


def _call_cerebras(prompt: str, want_json: bool) -> str:
    kw = {"response_format": {"type": "json_object"}} if want_json else {}
    r = _cerebras().chat.completions.create(
        model=CEREBRAS_MODEL,
        messages=[{"role": "user", "content": prompt}],
        **kw,
    )
    return r.choices[0].message.content


PROVIDERS = [
    ("gemini", _call_gemini),
    ("groq", _call_groq),
    ("cerebras", _call_cerebras),
]
_rotator = itertools.cycle(range(len(PROVIDERS)))
_rot_lock = threading.Lock()


def _next_start_idx() -> int:
    with _rot_lock:
        return next(_rotator)


def _is_rate_error(e: Exception) -> bool:
    msg = str(e).lower()
    return any(
        t in msg for t in ("429", "quota", "resource_exhausted", "rate limit", "rate_limit")
    )


def call_llm(prompt: str, want_json: bool = True) -> str:
    """Round-robin across 3 providers, rotate on 429, retry transient errors."""
    start_idx = _next_start_idx()
    last_err: Exception | None = None
    for offset in range(len(PROVIDERS)):
        name, fn = PROVIDERS[(start_idx + offset) % len(PROVIDERS)]
        for attempt in range(2):
            try:
                result = fn(prompt, want_json)
                if DEBUG:
                    print(f"    [llm] {name} served (attempt {attempt + 1})")
                return result
            except Exception as e:
                last_err = e
                if DEBUG:
                    print(f"    [llm] {name} failed: {str(e)[:120]}")
                if _is_rate_error(e):
                    break
                time.sleep(2 ** attempt)
    raise RuntimeError(f"all providers failed: {last_err}")
