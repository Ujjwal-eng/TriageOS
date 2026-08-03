from agents.specialist_factory import make_specialist
 
REFUND_THRESHOLD_INR = 1000.00
 
BILLING_SYSTEM_PROMPT = """You are a billing support specialist.
You can look up invoices, check payment status, and issue refunds.
Always look up the relevant invoice before proposing a refund.
Be concise and factual in your final response to the customer."""
 
BILLING_RISK_RULES = {
    "get_invoice": "low",
    "check_payment_status": "low",
    "issue_refund": lambda args: (
        "high" if args.get("amount", 0) > REFUND_THRESHOLD_INR else "low"
    ),
}
 
 
def build_billing_node(crm_tools: list):
    """crm_tools comes from mcp_client_config.load_all_tools()['crm'],
    loaded once when the app starts. Filters to just the tools billing needs
    (the CRM server also has account-related tools this agent shouldn't touch)."""
    needed = {"get_invoice", "check_payment_status", "issue_refund"}
    relevant_tools = [t for t in crm_tools if t.name in needed]
 
    return make_specialist(
        name="billing",
        tools=relevant_tools,
        system_prompt=BILLING_SYSTEM_PROMPT,
        risk_rules=BILLING_RISK_RULES,
    )
 
 
# --- One-time setup, done wherever app starts (e.g. api/main.py) ---
#
#   import asyncio
#   from mcp_client_config import load_all_tools
#   from agents.billing import build_billing_node
#
#   tools_by_server = asyncio.run(load_all_tools())
#   billing_node = build_billing_node(tools_by_server["crm"])
#
# `billing_node` is then just a normal function again from this point on —
# the async part only happens once, at startup, not on every ticket.
 
