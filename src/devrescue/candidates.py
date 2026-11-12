"""Sample k candidate answers per raw incident (for pairwise labeling).

    python -m devrescue.candidates --raw data/raw_incidents.jsonl --k 3 --out data/candidates.jsonl
"""
import argparse
import json

from .config import build_prompt
from .inference import diagnose


def dedupe(answers: list[str]) -> list[str]:
    seen, out = set(), []
    for a in answers:
        key = " ".join(a.lower().split())
        if key and key not in seen:
            seen.add(key)
            out.append(a)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--raw", required=True)
    ap.add_argument("--k", type=int, default=3)
    ap.add_argument("--temperature", type=float, default=0.9)
    ap.add_argument("--out", default="data/candidates.jsonl")
    a = ap.parse_args()
    with open(a.raw) as f, open(a.out, "w") as out:
        for line in f:
            r = json.loads(line)
            answers = dedupe([diagnose(r["kind"], r["text"], temperature=a.temperature) for _ in range(a.k)])
            if len(answers) >= 2:  # need at least two distinct answers to form a pair
                out.write(json.dumps({"prompt": build_prompt(r["kind"], r["text"]), "candidates": answers,
                                      "source": r.get("source")}) + "\n")


if __name__ == "__main__":
    main()
