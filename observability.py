"""
Two things live here:
 
1. log_event() — appends ONE line of JSON per node execution to
   logs/events.jsonl. Never overwrites — every call adds a new line, so
   the file becomes a running history across every run of the system.
   This is the fallback that works with zero external dependencies —
   worth having even though LangSmith gives us a richer version, because
   this one is fully ours, works offline, and we understand every part
   of how it works.
 
2. with_logging() — wraps any graph node (sync OR async) so it gets
   timed and logged automatically, without editing that node's own code
   at all. Same "wrap, don't rewrite" idea as specialist_factory.py.
"""
 
import functools
import inspect
import json
import time
from datetime import datetime, timezone
from pathlib import Path
 
LOG_DIR = Path(__file__).parent / "logs"
LOG_PATH = LOG_DIR / "events.jsonl"
 
 
def log_event(ticket_id: str, node_name: str, latency_ms: float,
               tokens: int = None, extra: dict = None) -> None:
    """Appends one structured event. tokens is optional — precise
    per-node token counts require reading each LLM response's
    usage_metadata inside that specific node, which is more invasive
    than this generic wrapper should be. LangSmith gives us that for
    free without this trade-off — another reason to use both."""
    LOG_DIR.mkdir(exist_ok=True)
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "ticket_id": ticket_id,
        "node": node_name,
        "latency_ms": round(latency_ms, 1),
        "tokens": tokens,
        "extra": extra or {},
    }
    with open(LOG_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")
 
 
def with_logging(node_fn, node_name: str):
    """Wraps a graph node function (sync OR async) so every call is
    automatically timed and logged. The wrapped node behaves exactly
    like the original from the graph's point of view — it just also
    logs on the way through. inspect.iscoroutinefunction() is how we
    decide which kind of wrapper to build, since sync and async
    functions have to be called differently (await vs. not)."""
 
    def _get_ticket_id(state: dict) -> str:
        return state.get("ticket_id") or state.get("customer_id") or "unknown"
 
    if inspect.iscoroutinefunction(node_fn):
        @functools.wraps(node_fn)
        async def async_wrapper(state: dict) -> dict:
            start = time.perf_counter()
            result = await node_fn(state)
            latency_ms = (time.perf_counter() - start) * 1000
            log_event(_get_ticket_id(state), node_name, latency_ms)
            return result
        return async_wrapper
 
    @functools.wraps(node_fn)
    def sync_wrapper(state: dict) -> dict:
        start = time.perf_counter()
        result = node_fn(state)
        latency_ms = (time.perf_counter() - start) * 1000
        log_event(_get_ticket_id(state), node_name, latency_ms)
        return result
    return sync_wrapper
 
