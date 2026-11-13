"""Synthetic preference-pair + labeled-incident generator (template based).

    python -m devrescue.synth --n 3000 --pairs data/pairs.jsonl --incidents data/incidents.jsonl

Good for bootstrapping/smoke-testing the DPO pipeline. It is NOT a substitute for real developer
preferences: templates give narrow coverage, so don't report accuracy measured on this data.
"""
import argparse
import json
import random
import zlib

# Each scenario: kind, input template, root-cause phrase, fixes, rejected (plausible-but-wrong) answers.
SCENARIOS = [
    dict(kind="stack_trace",
         text="Traceback (most recent call last):\n  File \"{f}.py\", line {n}, in <module>\n    import {m}\nModuleNotFoundError: No module named '{m}'",
         slots=dict(f=["app", "main", "worker", "train"], n=range(1, 80), m=["psycopg2", "yaml", "numpy", "redis", "requests"]),
         cause="{m} is not installed in the active environment",
         fixes=["pip install {m} (or its PyPI name)", "Add it to requirements.txt so CI and Docker builds include it"],
         bad=["Your Python installation is corrupted. Reinstall Python.", "Restart your machine and re-run the script."]),
    dict(kind="stack_trace",
         text="Traceback (most recent call last):\n  File \"{f}.py\", line {n}, in handler\n    return data[\"{k}\"]\nKeyError: '{k}'",
         slots=dict(f=["api", "service", "etl"], n=range(10, 200), k=["user_id", "email", "token", "items"]),
         cause="the '{k}' key is missing from the input dict",
         fixes=["Check the payload producer and confirm '{k}' is sent", "Use data.get('{k}') with validation and a clear error"],
         bad=["Python dictionaries are unreliable; switch to a list.", "Increase the server memory."]),
    dict(kind="stack_trace",
         text="java.lang.NullPointerException: Cannot invoke \"{o}.{m}()\" because \"{v}\" is null\n\tat com.acme.{c}.run({c}.java:{n})",
         slots=dict(o=["String", "User", "Order"], m=["length", "getId", "getTotal"], v=["name", "user", "order"], c=["Billing", "Checkout", "Sync"], n=range(20, 400)),
         cause="'{v}' is null when {m}() is called",
         fixes=["Trace where '{v}' is assigned and guard against null", "Add a null check or use Optional at the call site"],
         bad=["The JVM version is too old; upgrade Java.", "Clear the build cache and recompile."]),
    dict(kind="log",
         text="FATAL: password authentication failed for user \"{u}\"\nconnection to server at \"{h}\", port 5432 failed",
         slots=dict(u=["app", "etl", "api"], h=["db", "pg-prod", "postgres.internal"]),
         cause="the credentials the app uses do not match the Postgres user '{u}'",
         fixes=["Verify DATABASE_URL / secret values in the deployment", "Reset the role password if it was rotated, then redeploy"],
         bad=["Postgres is down. Restart the server.", "Open port 5432 in the firewall."]),
    dict(kind="log",
         text="{t} ERROR Container {c} exited with code 137 (OOMKilled)\nmemory limit: {l}Mi",
         slots=dict(t=["2025-03-02T10:11:12Z", "2025-06-18T22:01:45Z"], c=["api", "worker", "ingest"], l=[256, 512, 1024]),
         cause="the container exceeded its {l}Mi memory limit and was OOM-killed",
         fixes=["Profile memory usage and fix the leak or batch size", "Raise the memory limit if the workload legitimately needs it"],
         bad=["Exit code 137 means a syntax error in your code.", "Disable health checks."]),
    dict(kind="ci_failure",
         text="Step 4/7: RUN npm ci\nnpm ERR! code EUSAGE\nnpm ERR! `npm ci` can only install packages when your package.json and package-lock.json are in sync.\n({t})",
         slots=dict(t=["node 18", "node 20", "node 22"]),
         cause="package-lock.json is out of sync with package.json",
         fixes=["Run `npm install` locally to regenerate the lockfile", "Commit package-lock.json and re-run the pipeline"],
         bad=["npm is broken on the runner. Switch to yarn.", "Delete node_modules from the repo."]),
    dict(kind="ci_failure",
         text="FAILED tests/test_{t}.py::test_{t} - AssertionError\nE   assert {a} == {b}\nCI job: {j}",
         slots=dict(t=["pricing", "auth", "export"], a=[1, 2, 3], b=[4, 5, 6], j=["unit", "integration"]),
         cause="the code under test returns {a} while the test expects {b}, so a behavior change or stale expectation broke the test",
         fixes=["Check the latest diff touching {t} to see which side is right", "Fix the logic or update the expected value, then re-run the {j} job"],
         bad=["Re-run the job until it passes; it is flaky.", "Skip the test with @pytest.mark.skip."]),
    dict(kind="ci_failure",
         text="Error: Process completed with exit code 1.\ndocker: Error response from daemon: pull access denied for {i}, repository does not exist or may require 'docker login'",
         slots=dict(i=["acme/api", "acme/worker", "org/base-image"]),
         cause="the runner cannot pull {i}: the image name is wrong or registry credentials are missing",
         fixes=["Confirm the image name and tag exist in the registry", "Add or refresh the registry login secret used by the pipeline"],
         bad=["Docker is not installed on the runner.", "Increase the job timeout."]),
    dict(kind="log",
         text="{t} WARN connection pool exhausted: {n} waiting, max_pool_size={p}\nrequest GET /{e} timed out after 30s",
         slots=dict(t=["12:01:07", "03:44:51"], n=range(20, 90), p=[10, 20], e=["orders", "search"]),
         cause="the DB connection pool (max {p}) is exhausted, likely from leaked or long-held connections",
         fixes=["Find code paths that do not release connections and fix them", "Add query timeouts and size the pool to the workload"],
         bad=["The network is slow. Contact your ISP.", "Add more CSS caching."]),
]


def _fill(tpl: str, vals: dict) -> str:
    return tpl.format(**vals)


def _format_answer(cause: str, fixes: list[str]) -> str:
    return f"ROOT CAUSE: {cause}.\nFIX:\n" + "\n".join(f"{i}. {f}." for i, f in enumerate(fixes, 1))


def _hard_negative(sc: dict, prompt: str) -> str:
    """Well-formatted but WRONG: the diagnosis of a different scenario. Forces DPO to learn
    correctness, not just style. Uses its own rng so prompts don't depend on hard_frac."""
    r = random.Random(zlib.crc32(prompt.encode()))
    other = r.choice([x for x in SCENARIOS if x is not sc])
    v = {k: r.choice(list(vs)) for k, vs in other["slots"].items()}
    return _format_answer(_fill(other["cause"], v), [_fill(f, v) for f in other["fixes"]])


def make_example(rng: random.Random, hard_frac: float = 0.7):
    sc = rng.choice(SCENARIOS)
    vals = {k: rng.choice(list(v)) for k, v in sc["slots"].items()}
    prompt = f"[{sc['kind']}]\n{_fill(sc['text'], vals)}"
    cause = _fill(sc["cause"], vals)
    fixes = [_fill(f, vals) for f in sc["fixes"]]
    chosen = _format_answer(cause, fixes)
    easy = rng.choice(sc["bad"])  # always drawn so prompt sequence is independent of hard_frac
    hard = random.Random(zlib.crc32(prompt.encode()) + 1).random() < hard_frac
    rejected = _hard_negative(sc, prompt) if hard else easy
    return {"prompt": prompt, "chosen": chosen, "rejected": rejected}, {
        "kind": sc["kind"], "text": _fill(sc["text"], vals), "root_cause": cause,
    }


def generate(n: int, seed: int = 0, hard_frac: float = 0.7):
    rng = random.Random(seed)
    pairs, incidents, seen = [], [], set()
    attempts = 0
    while len(pairs) < n and attempts < n * 20:
        attempts += 1
        p, inc = make_example(rng, hard_frac)
        if p["prompt"] in seen:  # dedupe
            continue
        seen.add(p["prompt"])
        pairs.append(p)
        incidents.append(inc)
    return pairs, incidents


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=500)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--hard-frac", type=float, default=0.7, help="share of pairs whose rejected answer is a wrong-but-plausible diagnosis")
    ap.add_argument("--pairs", default="data/pairs.jsonl")
    ap.add_argument("--incidents", default="data/incidents.jsonl")
    a = ap.parse_args()
    pairs, incs = generate(a.n, a.seed, a.hard_frac)
    for path, rows in ((a.pairs, pairs), (a.incidents, incs)):
        with open(path, "w") as f:
            f.writelines(json.dumps(r) + "\n" for r in rows)
    print(f"wrote {len(pairs)} unique pairs -> {a.pairs}, {len(incs)} incidents -> {a.incidents}")


if __name__ == "__main__":
    main()
