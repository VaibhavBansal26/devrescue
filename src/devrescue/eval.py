"""Offline eval on labeled incidents.

JSONL rows: {"kind", "text", "root_cause"}
Metrics (all heuristic; use human / LLM-judge grading for numbers you publish):
  exact   - labeled root cause appears verbatim in the answer
  fuzzy   - >= 50% of the labeled root cause's content words appear in the answer's ROOT CAUSE line
            (or its first 300 chars if there is no such line)
  format  - answer starts with "ROOT CAUSE:"
Predictions are saved so re-scoring never needs re-generation.
"""
import argparse
import json
import re

STOP = {"the", "a", "an", "is", "are", "to", "of", "in", "and", "or", "when", "that", "it", "its", "so", "for", "from", "with", "be", "by", "on", "this", "has", "have", "as", "at"}


def _words(s: str) -> set[str]:
    toks = (w.strip(".-'_") for w in re.findall(r"[a-z0-9_\-\.']+", s.lower()))
    return {w for w in toks if w and w not in STOP}


def cause_line(answer: str) -> str:
    m = re.search(r"ROOT CAUSE:\s*(.*?)(?:\nFIX|\Z)", answer, re.S | re.I)
    # no labeled cause line: judge only the opening, so long rambling answers can't win on word overlap
    return m.group(1) if m else answer[:300]


def exact(answer: str, root_cause: str) -> bool:
    return root_cause.lower() in answer.lower()


def fuzzy(answer: str, root_cause: str, thresh: float = 0.5) -> bool:
    want = _words(root_cause)
    return bool(want) and len(want & _words(cause_line(answer))) / len(want) >= thresh


def score(rows, answers) -> dict:
    n = len(rows)
    return {
        "incidents": n,
        "exact": sum(exact(a, r["root_cause"]) for r, a in zip(rows, answers)) / n,
        "fuzzy": sum(fuzzy(a, r["root_cause"]) for r, a in zip(rows, answers)) / n,
        "format": sum(a.strip().upper().startswith("ROOT CAUSE:") for a in answers) / n,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", required=True)
    ap.add_argument("--preds", help="read/write predictions here (cached)")
    a = ap.parse_args()
    rows = [json.loads(l) for l in open(a.data) if l.strip()]
    try:
        answers = [json.loads(l)["answer"] for l in open(a.preds)] if a.preds else None
    except FileNotFoundError:
        answers = None
    if answers is None:
        from .inference import diagnose

        answers = [diagnose(r["kind"], r["text"]) for r in rows]
        if a.preds:
            open(a.preds, "w").write("".join(json.dumps({"answer": x}) + "\n" for x in answers))
    print(json.dumps(score(rows, answers)))


if __name__ == "__main__":
    main()
