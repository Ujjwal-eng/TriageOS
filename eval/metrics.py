"""
Computes the three metrics, kept as pure functions
(no LangGraph, no async, no I/O) so they're easy to unit-test on their
own with fake data before trusting them on real eval runs.
"""
 
from collections import defaultdict
 
 
def compute_routing_accuracy(results: list, gold_by_id: dict) -> dict:
    """results: list of {"ticket_id", "predicted_category", ...}
    Returns accuracy + a confusion matrix (gold -> predicted -> count)."""
    total = len(results)
    correct = 0
    confusion = defaultdict(lambda: defaultdict(int))
 
    for r in results:
        gold = gold_by_id[r["ticket_id"]]
        gold_cat = gold["gold_category"]
        pred_cat = r.get("predicted_category")
 
        confusion[gold_cat][pred_cat] += 1 # table bna rhe ki kitne predicted shi h v/s actual
        if pred_cat == gold_cat:
            correct += 1
 
    return {
        "accuracy": correct / total if total else 0.0,
        "correct": correct,
        "total": total,
        "confusion_matrix": {g: dict(preds) for g, preds in confusion.items()},# converting defaultdict back into plain, regular dictionaries
    }
 
 
def compute_escalation_metrics(results: list, gold_by_id: dict) -> dict:
    """Precision/recall on requires_human, treating a MISSED escalation
    (false negative) as the more costly error — this is the metric that
    demonstrates you understand that asymmetry, not just that you can
    compute precision/recall."""
    tp = fp = fn = tn = 0
 
    for r in results:
        gold = gold_by_id[r["ticket_id"]]
        gold_escalate = gold["gold_should_escalate"]
        pred_escalate = r.get("predicted_should_escalate", False)# agar kisi wajah se key nhi mil pati to default false(matlab escalate nhi krega)
 
        if gold_escalate and pred_escalate:
            tp += 1
        elif not gold_escalate and pred_escalate:
            fp += 1
        elif gold_escalate and not pred_escalate:
            fn += 1
        else:
            tn += 1
 #of all the times the agent escalated, how often was that actually necessary
    precision = tp / (tp + fp) if (tp + fp) else None
 #Of all the tickets that actually needed a human, how many did the agent catch   
    recall = tp / (tp + fn) if (tp + fn) else None
 
    return {
        "precision": precision,
        "recall": recall,
        "true_positives": tp,
        "false_positives": fp, # THE costly one — missed a ticket that needed a human
        "false_negatives": fn,   
        "true_negatives": tn,
    }
 
 
def compute_resolution_correctness(results: list, gold_by_id: dict) -> dict:
    """Keyword-presence check, ONLY on tickets gold-labeled as
    'should NOT escalate' — an escalated ticket has no fixed automated
    resolution to check against (a human writes it manually), so it's
    excluded rather than scored as a failure."""
    checked = 0
    correct = 0
    failures = []
 
    for r in results:
        gold = gold_by_id[r["ticket_id"]]
        if gold["gold_should_escalate"]:#aadmi khud likhega reply to check krne ki jrurat nhi h
            continue  # not applicable — no automated resolution to check
 
        required_words = gold.get("gold_resolution_contains", [])
        if not required_words:
            continue  # nothing specific to check for this ticket
 
        checked += 1
        resolution_text = (r.get("resolution") or "").lower()
        # if required_words (like refund) nhi h Ai generated reso_text me to missing+1
        missing = [w for w in required_words if w.lower() not in resolution_text]
 
        if not missing: # matlab missing h hi nhi matlab correct h
            correct += 1
        else:
            failures.append({"ticket_id": r["ticket_id"], "missing_words": missing})
 
    return {
        "accuracy": correct / checked if checked else None,
        "checked": checked,
        "correct": correct,
        "failures": failures,
    }
 
 
def compute_metrics(results: list, gold_by_id: dict) -> dict:
    """The single entry point run_eval.py calls."""
    return {
        "total_tickets": len(results),
        "routing": compute_routing_accuracy(results, gold_by_id),
        "escalation": compute_escalation_metrics(results, gold_by_id),
        "resolution": compute_resolution_correctness(results, gold_by_id),
    }
 
 
if __name__ == "__main__":
    # Quick sanity check with fake data — no LLM, no graph needed.
    fake_gold = {
        "t1": {"gold_category": "billing", "gold_should_escalate": False,
               "gold_resolution_contains": ["refund"]},
        "t2": {"gold_category": "account", "gold_should_escalate": True,
               "gold_resolution_contains": []},
    }
    fake_results = [
        {"ticket_id": "t1", "predicted_category": "billing",
         "predicted_should_escalate": False, "resolution": "Your refund is processed."},
        {"ticket_id": "t2", "predicted_category": "account",
         "predicted_should_escalate": False, "resolution": None},  # a MISSED escalation
    ]
    import json
    print(json.dumps(compute_metrics(fake_results, fake_gold), indent=2))
 
