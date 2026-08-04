"""
Runs every ticket in test_tickets.jsonl through the REAL graph (same one
test_full_graph.py uses), computes metrics, and saves a timestamped JSON
report so we can diff two runs later — that's what "regression tracking"
means: run this before a prompt change, run it again after, compare the
two JSON files.
 
IMPORTANT: this does NOT resume interrupted tickets with a human decision.
It only checks WHETHER a ticket correctly triggered human review — that's
all escalation precision/recall needs. Running with an actual human
approving/rejecting 20+ tickets isn't practical for an automated eval.
"""
 
import asyncio
import json
from datetime import datetime, timezone
from pathlib import Path
 
from mcp_client_config import load_all_tools
from graph.builder_graph import build_graph
from eval.metrics import compute_metrics
 
TICKETS_PATH = Path(__file__).parent / "test_tickets.jsonl"
RESULTS_DIR = Path(__file__).parent / "results"
 
 
def load_tickets() -> list:
    tickets = []
    with open(TICKETS_PATH, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                tickets.append(json.loads(line))
    return tickets
 
 
async def run_single_ticket(graph, ticket: dict) -> dict:
    thread_id = f"eval-{ticket['ticket_id']}"
    config = {"configurable": {"thread_id": thread_id}}
    initial_state = {"messages": [("human", ticket["text"])], "ticket_id": ticket["ticket_id"]}
 
    try:
        result = await graph.ainvoke(initial_state, config=config)
    except Exception as e:
        # A crashed ticket shouldn't kill the whole eval run — record it
        # as a failure and keep going, same instinct as your defensive
        # .get() fixes earlier.
        return {
            "ticket_id": ticket["ticket_id"],
            "predicted_category": None,
            "predicted_confidence": None,
            "predicted_should_escalate": None,
            "resolution": None,
            "error": str(e),
        }
 
    # If the graph is currently paused at an interrupt, requires_human
    # was set True at some point during this run.
    predicted_should_escalate = "__interrupt__" in result
 
    return {
        "ticket_id": ticket["ticket_id"],
        "predicted_category": result.get("category"),
        "predicted_confidence": result.get("confidence"),
        "predicted_should_escalate": predicted_should_escalate,
        "resolution": result.get("resolution"),
        "error": None,
    }
 
 
async def main():
    tickets = load_tickets()
    print(f"Loaded {len(tickets)} test tickets.")
 
    tools_by_server = await load_all_tools()
    graph = build_graph(tools_by_server)
 
    results = []
    for ticket in tickets:
        print(f"Running {ticket['ticket_id']}...")
        result = await run_single_ticket(graph, ticket)
        results.append(result)
        if result.get("error"):
            print(f"  ERROR: {result['error']}")
        else:
            print(f"  -> category={result['predicted_category']} "
                  f"escalate={result['predicted_should_escalate']}")
 
    gold_by_id = {t["ticket_id"]: t for t in tickets}
    report = compute_metrics(results, gold_by_id)
    report["raw_results"] = results
    report["run_timestamp"] = datetime.now(timezone.utc).isoformat()
 
    RESULTS_DIR.mkdir(exist_ok=True)
    filename = RESULTS_DIR / f"run_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.json"
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)
 
    print(f"\n{'=' * 50}")
    print("EVAL SUMMARY")
    print("=" * 50)
    print(f"Routing accuracy:      {report['routing']['accuracy']:.1%} "
          f"({report['routing']['correct']}/{report['routing']['total']})")
    print(f"Escalation precision:  {report['escalation']['precision']}")
    print(f"Escalation recall:     {report['escalation']['recall']}")
    print(f"  (false negatives — MISSED escalations: {report['escalation']['false_negatives']})")
    print(f"Resolution accuracy:   {report['resolution']['accuracy']} "
          f"({report['resolution']['checked']} checked)")
    print(f"\nFull report saved to: {filename}")
 
 
if __name__ == "__main__":
    asyncio.run(main())
 
