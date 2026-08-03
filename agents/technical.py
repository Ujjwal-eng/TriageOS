from agents.specialist_factory import make_specialist
 
TECHNICAL_SYSTEM_PROMPT = """You are a technical support specialist.
Use the knowledge base to find relevant help articles before answering.
If the issue looks like a real bug (not user error), file a debug ticket.
Be concise and give the customer clear next steps."""
 
TECHNICAL_RISK_RULES = {
    "search_kb": "low",
    "check_service_status": "low",
    "create_debug_ticket": "low",
}
 
 
def build_technical_node(kb_tools: list):
    """kb_tools comes from mcp_client_config.load_all_tools()['kb']."""
    needed = {"search_kb", "check_service_status", "create_debug_ticket"}
    relevant_tools = [t for t in kb_tools if t.name in needed]
 
    return make_specialist(
        name="technical",
        tools=relevant_tools,
        system_prompt=TECHNICAL_SYSTEM_PROMPT,
        risk_rules=TECHNICAL_RISK_RULES,
    )
 
 
# --- One-time setup, done wherever your app starts ---
#
#   tools_by_server = asyncio.run(load_all_tools())
#   technical_node = build_technical_node(tools_by_server["kb"])