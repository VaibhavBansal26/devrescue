"""Terminal labeling tool + pair builder.

    python -m devrescue.label --candidates data/candidates.jsonl --labeler alice --out data/labels.jsonl
    python -m devrescue.label --build --labels data/labels.jsonl --pairs data/real_pairs.jsonl
    python -m devrescue.label --agreement data/labels_alice.jsonl data/labels_bob.jsonl

Rubric: correct root cause first > ordered, actionable fix > no unsupported guesses.
"""
import argparse
import json
from pathlib import Path


def build_pairs(labels: list[dict]) -> list[dict]:
    pairs = []
    for l in labels:
        c = l["candidates"]
        b, w = l.get("best"), l.get("worst")
        if b is None or w is None or b == w:
            continue
        pairs.append({"prompt": l["prompt"], "chosen": c[b], "rejected": c[w]})
    return pairs


def agreement(a: list[dict], b: list[dict]) -> float:
    """Fraction of shared prompts where both labelers picked the same 'best' answer text."""
    bb = {x["prompt"]: x["candidates"][x["best"]] for x in b if x.get("best") is not None}
    shared = [(x["candidates"][x["best"]], bb[x["prompt"]]) for x in a if x.get("best") is not None and x["prompt"] in bb]
    return sum(p == q for p, q in shared) / len(shared) if shared else float("nan")


def _read(path):
    return [json.loads(l) for l in Path(path).read_text().splitlines() if l.strip()]


def label_loop(cands_path: str, out_path: str, labeler: str):
    done = {json.loads(l)["prompt"] for l in open(out_path)} if Path(out_path).exists() else set()
    with open(out_path, "a") as out:
        for row in _read(cands_path):
            if row["prompt"] in done:
                continue
            print("\n" + "=" * 70 + f"\n{row['prompt']}\n" + "=" * 70)
            for i, c in enumerate(row["candidates"]):
                print(f"\n--- [{i}] ---\n{c}")
            ans = input("\nbest worst (e.g. '0 2'), 's' skip, 'q' quit: ").strip().lower()
            if ans == "q":
                break
            if ans == "s" or len(ans.split()) != 2:
                continue
            best, worst = map(int, ans.split())
            out.write(json.dumps({**row, "best": best, "worst": worst, "labeler": labeler}) + "\n")
            out.flush()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--candidates")
    ap.add_argument("--labeler", default="me")
    ap.add_argument("--out", default="data/labels.jsonl")
    ap.add_argument("--build", action="store_true")
    ap.add_argument("--labels")
    ap.add_argument("--pairs", default="data/real_pairs.jsonl")
    ap.add_argument("--agreement", nargs=2)
    a = ap.parse_args()
    if a.agreement:
        print(f"best-answer agreement: {agreement(_read(a.agreement[0]), _read(a.agreement[1])):.2f}")
    elif a.build:
        pairs = build_pairs(_read(a.labels))
        Path(a.pairs).write_text("".join(json.dumps(p) + "\n" for p in pairs))
        print(f"wrote {len(pairs)} pairs -> {a.pairs}")
    else:
        label_loop(a.candidates, a.out, a.labeler)


if __name__ == "__main__":
    main()
