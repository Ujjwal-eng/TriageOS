"""
Combines PII redaction and injection detection into ONE node.
 
ORDER MATTERS: redact PII first, THEN run injection detection on the
already-redacted text. This means the injection classifier (which calls
an LLM) never sees raw PII either — one more place that data doesn't
need to travel through.
"""
 
from guardrails.pii import pii_ingest_node
from guardrails.injection_guard import injection_guard_node
 
 
async def ingest_node(state: dict) -> dict:
    # Step 1: redact PII (sync, no LLM call).
    pii_update = pii_ingest_node(state)
 
    # Apply that update to a temporary merged view so injection detection
    # sees the REDACTED text, not the original raw message.
    state_after_pii = {**state, **pii_update}
 
    # Step 2: check the (now PII-safe) text for injection attempts (async, LLM call).
    injection_update = await injection_guard_node(state_after_pii)
 
    # Combine both partial updates into one return value.
    combined = dict(pii_update)
    combined.update(injection_update)
    return combined
 
