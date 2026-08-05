"""
Turns the raw logs/events.jsonl file into a readable summary table —
average and max latency per node, call counts, total tickets seen.
"""
 
import json
from collections import defaultdict
from pathlib import Path
 
LOG_PATH = Path(__file__).parent.parent / "logs" / "events.jsonl"
 
 
def load_events() -> list:
    events = []
    if not LOG_PATH.exists():
        return events
    with open(LOG_PATH, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                events.append(json.loads(line))
    return events
 
 
def summarize(events: list) -> None:
    if not events:
        print(f"No events found at {LOG_PATH}. Run a graph (e.g. "
              f"test_full_graph.py) first to generate some.")
        return
 
    by_node = defaultdict(list)
    tickets_seen = set()
 
    for e in events:
        by_node[e["node"]].append(e["latency_ms"])
        tickets_seen.add(e["ticket_id"])
 
    print(f"{'NODE':<18} {'CALLS':>6} {'AVG (ms)':>10} {'MAX (ms)':>10}")
    print("-" * 48)
    for node, latencies in sorted(by_node.items(), key=lambda x: -sum(x[1])):
        avg = sum(latencies) / len(latencies)
        print(f"{node:<18} {len(latencies):>6} {avg:>10.1f} {max(latencies):>10.1f}")
 
    print("-" * 48)
    print(f"Total tickets logged: {len(tickets_seen)}")
    print(f"Total events logged:  {len(events)}")
 
 
if __name__ == "__main__":
    summarize(load_events())
 
