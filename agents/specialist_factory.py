"""
One function that builds any specialist agent (billing / technical / account).
Instead of writing three near-identical agent loops, we write the loop once
and each specialist just supplies: its name, its tools, its prompt, and its
risk rules.
 
THE LOOP, IN PLAIN ENGLISH:
  1. Ask the model what to do next.
  2. If it just wants to reply with text -> we're done, return the resolution.
  3. If it wants to call a tool -> check whether that tool is "risky" first.
       - Risky  -> STOP. Don't run it. Flag for human review instead.
       - Safe   -> actually run the tool, show the model the result, go to 1.
  4. If this loops more than `max_iterations` times without finishing,
     treat that as a problem and flag it for a human too (an agent that
     can't resolve something after several tries shouldn't fail silently).
"""
import os
from dotenv import load_dotenv
load_dotenv()

from langchain_groq import ChatGroq
from langchain_core.messages import ToolMessage
 
 
def _get_risk_level(tool_name: str, args: dict, risk_rules: dict) -> str:
    """risk_rules maps tool_name -> "low"/"high", OR tool_name -> a function
    that looks at the tool's arguments and decides. This is what lets the
    billing agent say 'issue_refund is only risky above ₹1000' instead of
    every refund being high risk regardless of amount."""
    rule = risk_rules.get(tool_name, "low")
    if callable(rule):
        return rule(args)
    return rule
 
 
def make_specialist(name: str, tools: list, system_prompt: str,
                     risk_rules: dict, max_iterations: int = 4):
    """Returns a graph-node function for this specialist."""
 
    llm = ChatGroq(model="llama-3.3-70b-versatile", temperature=0)
    llm_with_tools = llm.bind_tools(tools)
    tools_by_name = {t.name: t for t in tools}
 
    async def node(state: dict) -> dict:
        messages = [("system", system_prompt)] + list(state["messages"])
 
        for _ in range(max_iterations):
            response = await llm_with_tools.ainvoke(messages)
            messages.append(response)
 
            # No tool call requested -> the model is giving a final answer.
            if not response.tool_calls:
                return {
                    "resolution": response.content,
                    "risk_level": "low",
                    "requires_human": False,
                }
 
            # One or more tool calls requested. Check each before running it.
            for call in response.tool_calls:
                tool_name, args = call["name"], call["args"]
                risk = _get_risk_level(tool_name, args, risk_rules)
 
                if risk == "high":
                    return {
                        "risk_level": "high",
                        "proposed_action": {"tool": tool_name, "args": args},
                        "requires_human": True,
                        "escalation_reason": (
                            f"{name} agent wants to call high-risk tool "
                            f"'{tool_name}' with args {args}"
                        ),
                    }
 
                # Low risk -> actually execute it and feed the result back.
                result =await tools_by_name[tool_name].ainvoke(args)
                messages.append(ToolMessage(content=str(result),
                                             tool_call_id=call["id"]))
 
        # Exceeded max_iterations without a final answer or an escalation.
        return {
            "risk_level": "high",
            "requires_human": True,
            "escalation_reason": (
                f"{name} agent exceeded {max_iterations} tool-call "
                f"iterations without resolving the ticket"
            ),
        }
 
    return node
 
