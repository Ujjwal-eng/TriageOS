"""
The full shared state schema — every field any node in the real graph
reads or writes. This is the "folder" every agent shares, built up from
every phase: messages (Phase 1), category/confidence (triage),
risk_level/proposed_action (specialists), escalation_reason/human_decision
(escalation), redacted_pii (guardrails), resolution (final output).
"""
 
from typing import TypedDict, Optional
 
 
class SupportState(TypedDict, total=False):
    messages: list
    ticket_id: Optional[str]
    customer_id: Optional[str]
 
    category: Optional[str]
    confidence: Optional[float]
 
    risk_level: Optional[str]
    proposed_action: Optional[dict]
    requires_human: bool
    escalation_reason: Optional[str]
 
    redacted_pii: dict
    human_decision: Optional[dict]
 
    resolution: Optional[str]
 
