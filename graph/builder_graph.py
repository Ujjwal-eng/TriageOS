"""
Wires every piece built across Phases 1-6 into one real graph:
 
  ingest -> triage -> (specialist OR escalate)
  specialist -> risk_check -> (human_review OR output_validate)
  human_review -> apply_decision -> output_validate -> END
"""
 
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
 
from graph.state import SupportState
from graph.router import route_by_confidence_and_category, route_by_risk,route_after_output_validate
 
from guardrails.ingest import ingest_node
from agents.triage import triage_node
from agents.billing import build_billing_node
from agents.technical import build_technical_node
from agents.account import build_account_node
from agents.escalation import human_review, build_apply_decision_node
from guardrails.output_validator import output_validator_node
from observability import with_logging
 
def risk_check_node(state: dict) -> dict:
    """A defensive pass-through, not a place that computes NEW risk logic.
    Your specialists (via specialist_factory) already decide risk_level
    and requires_human themselves — this node exists as an explicit,
    visible checkpoint in the graph, and gives you one safe place to add
    cross-cutting risk rules later (e.g. 'always escalate tickets from
    VIP customers') without touching any specialist's code."""
    return {
        "risk_level": state.get("risk_level", "low"),
        "requires_human": state.get("requires_human", False),
    }
 
 
def build_graph(tools_by_server: dict):
    """tools_by_server comes from mcp_client_config.load_all_tools() —
    call that ONCE when your app starts, then pass the result here."""
 
    billing_node = build_billing_node(tools_by_server["crm"])
    technical_node = build_technical_node(tools_by_server["kb"])
    account_node = build_account_node(tools_by_server["crm"])
 
    all_tools_by_name = {
        t.name: t for tools in tools_by_server.values() for t in tools
    }
    apply_decision = build_apply_decision_node(all_tools_by_name)
 
    builder = StateGraph(SupportState)
 
    builder.add_node("ingest", with_logging(ingest_node, "ingest"))
    builder.add_node("triage", with_logging(triage_node, "triage"))
    builder.add_node("billing", with_logging(billing_node, "billing"))
    builder.add_node("technical", with_logging(technical_node, "technical"))
    builder.add_node("account", with_logging(account_node, "account"))
    builder.add_node("risk_check", with_logging(risk_check_node, "risk_check"))
    builder.add_node("human_review", with_logging(human_review, "human_review"))
    builder.add_node("apply_decision", with_logging(apply_decision, "apply_decision"))
    builder.add_node("output_validate", with_logging(output_validator_node, "output_validate"))
 
 
    builder.set_entry_point("ingest")
    builder.add_edge("ingest", "triage")
 
    builder.add_conditional_edges("triage", route_by_confidence_and_category, {
        "billing": "billing",
        "technical": "technical",
        "account": "account",
        "escalate": "human_review",
    })
 
    for specialist in ["billing", "technical", "account"]:
        builder.add_edge(specialist, "risk_check")
 
    builder.add_conditional_edges("risk_check", route_by_risk, {
        "high": "human_review",
        "low": "output_validate",
    })
 
    builder.add_edge("human_review", "apply_decision")
    builder.add_edge("apply_decision", "output_validate")
    builder.add_conditional_edges("output_validate", route_after_output_validate, {
        "human_review": "human_review",
        "end": END,
    })
    return builder.compile(checkpointer=MemorySaver())