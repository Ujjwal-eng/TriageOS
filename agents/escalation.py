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

    def _parse_tool_result(raw):
        """Extract a plain dict from the raw tool.ainvoke() return value.
        LangChain wraps MCP tool output in content-block lists like
        [{'type':'text','text':'{...}','id':'...'}].  We unwrap that here
        so the rest of the code always works with a simple dict/string."""
        import json as _json

        # Already a dict — nothing to do.
        if isinstance(raw, dict):
            return raw

        # Content-block list — grab the first text block.
        if isinstance(raw, list):
            for block in raw:
                if isinstance(block, dict) and block.get("type") == "text":
                    try:
                        return _json.loads(block["text"])
                    except (ValueError, KeyError):
                        return {"result": block.get("text", str(raw))}
            return {"result": str(raw)}

        # Plain string (maybe JSON).
        if isinstance(raw, str):
            try:
                return _json.loads(raw)
            except ValueError:
                return {"result": raw}

        return {"result": str(raw)}

    def _friendly_message(tool_name: str, data: dict, edited: bool = False) -> str:
        """Turn a tool name + parsed result dict into a clear, customer-facing
        resolution message."""
        prefix = "Approved (edited)" if edited else "Approved"

        if tool_name == "issue_refund":
            amount = data.get("refunded", data.get("amount", "unknown"))
            cid = data.get("customer_id", "unknown")
            reason = data.get("reason", "")
            msg = f"{prefix}: Refund of ₹{amount:,.2f} issued to customer {cid}."
            if reason:
                msg += f" Reason: {reason}."
            return msg

        if tool_name == "delete_account":
            cid = data.get("customer_id", "unknown")
            deleted = data.get("deleted", False)
            if deleted:
                return f"{prefix}: Account {cid} has been permanently deleted."
            return f"{prefix}: Account deletion requested for {cid}."

        if tool_name == "update_email":
            cid = data.get("customer_id", "unknown")
            email = data.get("new_email", "unknown")
            return f"{prefix}: Email for customer {cid} updated to {email}."

        if tool_name == "reset_password":
            cid = data.get("customer_id", "unknown")
            return f"{prefix}: Password reset email sent to customer {cid}."

        if tool_name == "send_email":
            to = data.get("to", "unknown")
            return f"{prefix}: Email sent to {to}."

        # Fallback — show a clean summary of key-value pairs.
        details = ", ".join(f"{k}: {v}" for k, v in data.items()
                           if k not in ("id", "type"))
        return f"{prefix}: {tool_name} completed. {details}" if details else f"{prefix}: {tool_name} completed successfully."

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
            data = _parse_tool_result(result)
            return {
                "resolution": _friendly_message(proposed["tool"], data, edited=False),
                "requires_human": False,
            }

        elif action == "edit":
            edited = decision.get("edited_action", proposed)
            tool = all_tools_by_name.get(edited.get("tool"))
            if tool is None:
                return {"resolution": "Error: edited tool not found.",
                        "requires_human": False}
            result = await tool.ainvoke(edited.get("args", {}))
            data = _parse_tool_result(result)
            return {
                "resolution": _friendly_message(edited["tool"], data, edited=True),
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
 
