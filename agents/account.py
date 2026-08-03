from agents.specialist_factory import make_specialist
 
ACCOUNT_SYSTEM_PROMPT = """You are an account support specialist.
You can look up account info and reset passwords freely.
Email changes and account deletion are sensitive — you may propose them,
but they will always require human approval before happening.
Be concise and confirm what you did (or proposed) clearly."""
 
ACCOUNT_RISK_RULES = {
    "get_account_info": "low",
    "reset_password": "low",
    "update_email": "high",     # always — hardcoded, not the model's call
    "delete_account": "high",   # always — hardcoded, not the model's call
}
 
def build_account_node(crm_tools: list):
    """crm_tools comes from mcp_client_config.load_all_tools()['crm'].
    Note billing.py filters the SAME crm_tools list down to different tools —
    both agents share one CRM server but only see the tools relevant to them."""
    needed = {"get_account_info", "update_email", "reset_password", "delete_account"}
    relevant_tools = [t for t in crm_tools if t.name in needed]
 
    return make_specialist(
        name="account",
        tools=relevant_tools,
        system_prompt=ACCOUNT_SYSTEM_PROMPT,
        risk_rules=ACCOUNT_RISK_RULES,
    )
 
 
# --- One-time setup, done wherever app starts ---
#
#   tools_by_server = asyncio.run(load_all_tools())
#   account_node = build_account_node(tools_by_server["crm"])
