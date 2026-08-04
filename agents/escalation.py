"""
Two pieces live here:
 
1. human_review(state)
   The node where the graph actually PAUSES. Not "returns an answer
   quickly" — actually freezes, saves its exact state to the checkpointer,
   and waits. Could be seconds later, could be hours later, in a totally
   separate process (a human looking at a dashboard) that resumes it.
 
2. build_apply_decision_node(all_tools_by_name)
   Runs AFTER a human responds:
     - approve -> actually run the proposed action for real
     - edit    -> run the human's modified version of the action
     - reject  -> don't run anything, respond with a decline
   It needs access to every tool across every MCP server (not just one
   specialist's tools) because the human might approve ANY specialist's
   proposed action — this node doesn't know in advance which one.
"""
 
from langgraph.types import interrupt
 
 
def human_review(state: dict) -> dict:
    """The interrupt point. `interrupt()` pauses graph execution here and
    returns its argument as the payload a human reviewer sees. Whatever
    the human sends back when resuming becomes this function's return
    value — the `decision` variable below."""
    messages = state.get("messages", [])
    decision = interrupt({
        "reason": state.get("escalation_reason"),
        "proposed_action": state.get("proposed_action"),
        "ticket_context": messages[-3:] if messages else [],
    })
    return {"human_decision": decision}
 
 
def build_apply_decision_node(all_tools_by_name: dict):
    """all_tools_by_name: every tool from every MCP server, keyed by name.
    Build this once at startup by merging tools_by_server["crm"],
    ["kb"], ["email"] together — see test_escalation.py for the pattern."""
 
    async def apply_decision(state: dict) -> dict:
        decision = state.get("human_decision") or {}
        action = decision.get("action")
        proposed = state.get("proposed_action") or {}
 
        if action == "approve":
            tool = all_tools_by_name.get(proposed.get("tool"))
            if tool is None:
                return {"resolution": "Error: proposed tool not found.",
                        "requires_human": False}
            result = await tool.ainvoke(proposed.get("args", {}))
            return {
                "resolution": f"Approved and completed: {proposed['tool']} -> {result}",
                "requires_human": False,
            }
 
        elif action == "edit":
            edited = decision.get("edited_action", proposed)
            tool = all_tools_by_name.get(edited.get("tool"))
            if tool is None:
                return {"resolution": "Error: edited tool not found.",
                        "requires_human": False}
            result = await tool.ainvoke(edited.get("args", {}))
            return {
                "resolution": f"Approved (edited) and completed: {edited['tool']} -> {result}",
                "requires_human": False,
            }
 
        elif action == "manual_resolution":
            # Used when there's no proposed_action to approve at all —
            # e.g. a low-confidence routing escalation, or a suspected
            # injection ticket. A human just writes the reply directly.
            # `.strip()` + `or` here (not just `.get()`) because an EMPTY
            # reply (human hit Enter with nothing typed) still counts as
            # "text" being present in the dict — .get()'s default only
            # covers a missing key, not a blank value.
            reply_text = (decision.get("text") or "").strip()
            return {
                "resolution": reply_text or "A support representative will follow up with you directly.",
                "requires_human": False,
            }
 
        else:  # "reject" or anything unrecognized — fail safe, don't act
            return {
                "resolution": (
                    "We're unable to process this request automatically. "
                    "A support representative will follow up with you directly."
                ),
                "requires_human": False,
            }
 
    return apply_decision
 
