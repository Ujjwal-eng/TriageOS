"""
The "minimal reviewer interface" — no dashboard, just a
terminal prompt.
"""
 
from langgraph.types import Command
 
 
async def run_ticket_with_review(graph, initial_state: dict, thread_id: str) -> dict:
    """Runs a ticket through the graph. If it hits human_review, prompts
    the terminal for a decision and resumes. Returns the final state."""
    config = {"configurable": {"thread_id": thread_id}}
    result = await graph.ainvoke(initial_state, config=config)
 
    # Keep resuming in case a ticket somehow needs review more than once.
    while "__interrupt__" in result:
        payload = result["__interrupt__"][0].value
        proposed = payload.get("proposed_action")
 
        print("\n=== HUMAN REVIEW NEEDED ===")
        print(f"Reason:           {payload.get('reason')}")
        print(f"Proposed action:  {proposed}")
        print(f"Recent messages:  {payload.get('ticket_context')}")
 
        if not proposed:
            # No specific action to approve — e.g. a low-confidence routing
            # escalation, or a suspected injection ticket. Ask for a direct reply.
            print("\nNo specific action was proposed (likely a routing or "
                  "safety escalation).")
            reply_text = input("Type a reply to send the customer: ").strip()
            decision = {"action": "manual_resolution", "text": reply_text}
            result = await graph.ainvoke(Command(resume=decision), config=config)
            continue
 
        choice = input("\nApprove / Reject / Edit? (a/r/e): ").strip().lower()
 
        if choice == "a":
            decision = {"action": "approve"}
 
        elif choice == "e":
            print(f"Current args: {proposed.get('args')}")
            key = input("Which argument to change? ").strip()
            new_value = input(f"New value for '{key}': ").strip()
            edited_args = dict(proposed.get("args", {}))
            # Naive type handling — good enough for a demo CLI, not production input parsing.
            try:
                edited_args[key] = float(new_value)
            except ValueError:
                edited_args[key] = new_value
            decision = {
                "action": "edit",
                "edited_action": {"tool": proposed.get("tool"), "args": edited_args},
            }
 
        else:
            decision = {"action": "reject"}
 
        result = await graph.ainvoke(Command(resume=decision), config=config)
 
    return result
 
