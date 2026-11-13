# DevRescue: RLHF-aligned troubleshooting assistant

Diagnoses logs, stack traces and CI/CD failures. A base instruct model (Qwen2.5-0.5B-Instruct) is
aligned to developer preferences with **DPO + LoRA** (TRL/PEFT) and served through **FastAPI** with
**PostgreSQL** storage.

```
raw failures -> collect.py (redacted) -> candidates.py -> label.py -> pairs.jsonl -> train_dpo.py -> adapter
developer -> /diagnose -> model(+adapter) -> incidents table -> /incidents/{id}/resolve -> /metrics
          -> /feedback (1-5 ratings) -> feedback table -> pairs
```

## Status: working pipeline, **no real-world results yet**
Everything below was measured on **synthetic data** (9 templated error types) and is a pipeline
sanity check, not a claim about real incidents.

| 26 held-out synthetic incidents | Base | DPO (easy negatives) | DPO (hard negatives) |
|---|---|---|---|
| Root-cause word overlap (heuristic) | 0.88 | 0.50 | 0.81 |
| Uses `ROOT CAUSE:` format | 0% | 100% | 100% |
| Avg answer length (chars) | 1,074 | 224 | 194 |

- With only absurd rejected answers ("reinstall Python"), DPO learned style, not correctness.
- Rejected answers that are well-formatted but *wrong* (`synth.py --hard-frac`) recovered most of the accuracy
  while keeping the short, structured output. All remaining misses are one template.
- The judge is word overlap, so it is biased and noisy; n=26 is tiny. Don't read the gap as significant.

**Not yet done:** real incident data and human labels, an LLM/human judge, SFT warm-up, hyperparameter
sweeps, a fix-time study. See the roadmap below.

## Run
```bash
pip install -r requirements.txt && export PYTHONPATH=src
python -m devrescue.synth --n 1000                               # synthetic pairs (smoke test only)
python -m devrescue.train_dpo --data data/pairs.jsonl --out artifacts/dpo-lora
DEVRESCUE_ADAPTER_DIR=artifacts/dpo-lora python -m devrescue.eval --data data/incidents.jsonl
docker compose up --build                                        # API + Postgres on :8000
pytest
```
Training on Apple silicon works but is slow (about 3 hours for 1,000 pairs, 1 epoch); use a CUDA GPU for real runs.
Checkpoints save every 25 steps; per-epoch eval is off by default (`--eval`) because it ran out of memory on MPS.

## Real-data workflow
```bash
python -m devrescue.collect --repos owner/repo --per-repo 20     # failed GitHub Actions logs, redacted
python -m devrescue.candidates --raw data/raw_incidents.jsonl --k 3
python -m devrescue.label --candidates data/candidates.jsonl --labeler me   # pick best/worst per incident
python -m devrescue.label --build --labels data/labels.jsonl --pairs data/real_pairs.jsonl
```

## Roadmap
1. Collect and label several hundred real incidents; freeze a held-out real eval set.
2. SFT warm-up, then DPO on real + hard-negative pairs; sweep beta / lr / LoRA rank on a CUDA GPU.
3. Rubric-based LLM judge validated against hand-graded samples; confidence intervals.
4. Structured JSON output, auth/rate limits, pgvector retrieval, GitHub Action that comments diagnoses.
