"""Collect real CI failures from public GitHub Actions runs (via the `gh` CLI).

    python -m devrescue.collect --repos owner/a owner/b --per-repo 20 --out data/raw_incidents.jsonl

Logs are redacted (tokens, emails, credentials in URLs) and truncated to the tail before saving.
Only collect from repos whose licenses/terms allow it, and keep rate limits in mind.
"""
import argparse
import json
import subprocess

from .redact import redact


def _gh(*args: str) -> str:
    return subprocess.run(["gh", *args], capture_output=True, text=True, check=True).stdout


def failed_runs(repo: str, limit: int) -> list[dict]:
    out = _gh("run", "list", "--repo", repo, "--status", "failure", "-L", str(limit),
              "--json", "databaseId,name,url")
    return json.loads(out)


def run_log(repo: str, run_id: int) -> str:
    return _gh("run", "view", str(run_id), "--repo", repo, "--log-failed")


def collect(repos: list[str], per_repo: int):
    for repo in repos:
        for run in failed_runs(repo, per_repo):
            try:
                text = redact(run_log(repo, run["databaseId"]))
            except subprocess.CalledProcessError:
                continue  # logs expired or unavailable
            if len(text.strip()) < 50:
                continue
            yield {"kind": "ci_failure", "text": text, "source": run["url"], "repo": repo}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repos", nargs="+", required=True)
    ap.add_argument("--per-repo", type=int, default=20)
    ap.add_argument("--out", default="data/raw_incidents.jsonl")
    a = ap.parse_args()
    n = 0
    with open(a.out, "w") as f:
        for row in collect(a.repos, a.per_repo):
            f.write(json.dumps(row) + "\n")
            n += 1
    print(f"saved {n} incidents -> {a.out}")


if __name__ == "__main__":
    main()
