"""Preference data utilities. Format: JSONL with {prompt, chosen, rejected}."""
import json
import random
from pathlib import Path

from .config import SYSTEM_PROMPT


def load_pairs(path: str) -> list[dict]:
    rows = [json.loads(l) for l in Path(path).read_text().splitlines() if l.strip()]
    for r in rows:
        missing = {"prompt", "chosen", "rejected"} - r.keys()
        if missing:
            raise ValueError(f"row missing {missing}: {r}")
    return rows


def to_chat(rows: list[dict]) -> list[dict]:
    """Convert to TRL conversational preference format."""
    out = []
    for r in rows:
        out.append(
            {
                "prompt": [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": r["prompt"]},
                ],
                "chosen": [{"role": "assistant", "content": r["chosen"]}],
                "rejected": [{"role": "assistant", "content": r["rejected"]}],
            }
        )
    return out


def split(rows: list[dict], eval_frac: float = 0.1, seed: int = 0):
    rows = rows[:]
    random.Random(seed).shuffle(rows)
    n = max(1, int(len(rows) * eval_frac))
    return rows[n:], rows[:n]


def export_from_db(session, out_path: str, min_gap: int = 1) -> int:
    """Turn stored developer feedback (ratings on candidate answers) into pairs."""
    from .db import Feedback

    by_prompt: dict[str, list[Feedback]] = {}
    for fb in session.query(Feedback).all():
        by_prompt.setdefault(fb.prompt, []).append(fb)
    n = 0
    with open(out_path, "w") as f:
        for prompt, fbs in by_prompt.items():
            fbs.sort(key=lambda x: x.rating)
            lo, hi = fbs[0], fbs[-1]
            if hi.rating - lo.rating >= min_gap:
                f.write(json.dumps({"prompt": prompt, "chosen": hi.response, "rejected": lo.response}) + "\n")
                n += 1
    return n
