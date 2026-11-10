"""Offline eval on labeled incidents.

JSONL rows: {"kind", "text", "root_cause": "<keyword or phrase>", "baseline_minutes": float}
Root-cause accuracy = fraction of answers whose diagnosis contains the labeled root cause
(case-insensitive). Swap `judge` for human or LLM-as-judge grading for real numbers.
"""
import argparse
import json

from .inference import diagnose


def judge(answer: str, root_cause: str) -> bool:
    return root_cause.lower() in answer.lower()


def accuracy(rows, predict=diagnose) -> float:
    hits = sum(judge(predict(r["kind"], r["text"]), r["root_cause"]) for r in rows)
    return hits / len(rows)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", required=True)
    a = ap.parse_args()
    rows = [json.loads(l) for l in open(a.data) if l.strip()]
    print(f"incidents={len(rows)} root_cause_accuracy={accuracy(rows):.3f}")


if __name__ == "__main__":
    main()
