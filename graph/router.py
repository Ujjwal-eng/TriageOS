"""
The routing DECISIONS, kept separate from the graph WIRING (builder_graph.py)
so the actual logic — "which path does this ticket take?" — can be read
and tested on its own, without needing to understand LangGraph's syntax.
"""
 
CONFIDENCE_THRESHOLD = 0.6  
 
_VALID_CATEGORIES = {"billing", "technical", "account"}
 
 
def route_by_confidence_and_category(state: dict) -> str:
    """Runs right after triage. Decides: send to a specialist, or
    escalate straight to a human without ever reaching one."""
 
    # An earlier guardrail (ingest) may have ALREADY flagged this ticket
    # (e.g. suspected injection) before triage even ran. Respect that
    # first, regardless of what triage itself thinks.
    if state.get("requires_human"):
        return "escalate"
 
    category = state.get("category")
    confidence = state.get("confidence") or 0.0
 
    if confidence < CONFIDENCE_THRESHOLD or category not in _VALID_CATEGORIES:
        return "escalate"
 
    return category
 
 
def route_by_risk(state: dict) -> str:
    """Runs after a specialist has done its work (and risk_check has
    passed through). Decides: does a human need to sign off before this
    goes to the customer?"""
    return "high" if state.get("requires_human") else "low"
 
def route_after_output_validate(state: dict) -> str:
    """If validation failed AND we haven't already retried once, loop
    back to a human. Capped at 1 retry so a message that keeps failing
    validation can't cycle through the graph forever."""
    if state.get("requires_human") and state.get("validation_attempts", 0) <= 1:
        return "human_review"
    return "end"