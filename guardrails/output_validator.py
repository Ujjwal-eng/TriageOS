
"""
Runs on any text about to be shown to the customer — the final checkpoint
before a message goes out. Checks three things:
1. PII leakage (reuses guardrails/pii.py's detection — no separate logic)
2. Claims of an action that was never actually executed (hallucination check)
3. Length (tone/reject/editing middleware plugs in here — see note below)
 
Deliberately does NOT auto-fix anything it finds. Silently rewriting a
customer-facing message can hide a real problem instead of surfacing it —
a failed validation should route to a human, not get quietly patched.
"""
 
from guardrails.pii import contains_pii
 
_REFUND_CLAIM_PHRASES = ["refund issued", "refund has been processed", "refunded your", "money back"]
_ACCOUNT_CHANGE_PHRASES = ["email has been updated", "account has been deleted", "password has been reset"]
 
 
def _claims_unexecuted_action(text: str, proposed_action) -> bool:
    """Heuristic: the output CLAIMS an action happened, but no action was
    actually executed (no proposed_action, and no sign this went through
    apply_decision). Cheap keyword check — good enough to catch a model
    hallucinating a resolution it never actually performed."""
    lowered = text.lower()
    claim_phrases = _REFUND_CLAIM_PHRASES + _ACCOUNT_CHANGE_PHRASES
    action_claimed = any(phrase in lowered for phrase in claim_phrases)
    action_was_taken = (
        bool(proposed_action)
        or "approved and completed" in lowered
        or "approved (edited)" in lowered
    )
    return action_claimed and not action_was_taken
 
 
def validate_output(text: str, state: dict, max_length: int = 800) -> dict:
    """Returns {"passed": bool, "issues": [list of strings]}."""
    issues = []
 
    if contains_pii(text):
        issues.append("Output contains what looks like PII.")
 
    if _claims_unexecuted_action(text, state.get("proposed_action")):
        issues.append("Output claims an action was completed that wasn't actually executed.")
 
    if len(text) > max_length:
        issues.append(f"Output exceeds max length ({len(text)} > {max_length} chars).")
 
    # --- Will plug middleware here ---
 
    return {"passed": len(issues) == 0, "issues": issues}
 
 
def output_validator_node(state: dict) -> dict:
    """Graph node version — checks state['resolution'], escalates to a
    human if validation fails instead of letting a bad message through."""
    text = state.get("resolution") or "" # resolution is the msg that AI drafted from the ticket state
    result = validate_output(text, state)
 
    if result["passed"]:
        return {}
 
    return {
        "requires_human": True,
        "escalation_reason": "Output validation failed: " + "; ".join(result["issues"]),
    }
 
 
if __name__ == "__main__":
    # A message that hallucinates a refund it never actually issued.
    fake_state = {"proposed_action": None}
    bad_output = "Great news! Your refund has been processed and you'll see it in 3-5 days."
    print(validate_output(bad_output, fake_state))
 
    # A clean message that should pass.
    good_output = "I looked into your account and everything looks up to date."
    print(validate_output(good_output, fake_state))
 
