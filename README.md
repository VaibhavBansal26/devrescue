# DevRescue: RLHF-aligned troubleshooting assistant

Diagnoses logs, stack traces and CI/CD failures. A base instruct model is aligned to developer
preferences with **DPO + LoRA** (TRL/PEFT) and served through **FastAPI** with **PostgreSQL** storage.

```
developer -> /diagnose -> model (+LoRA adapter) -> incidents table
          -> /feedback (rate answers 1-5) -> feedback table -> pairs.jsonl -> DPO -> new adapter
          -> /incidents/{id}/resolve -> /metrics (root-cause accuracy, avg fix time)
```

## Run
```bash
pip install -r requirements.txt && export PYTHONPATH=src
python -m devrescue.train_dpo --data data/pairs.sample.jsonl   # replace with your 3,000+ pairs
python -m devrescue.eval --data data/incidents.jsonl           # your labeled incidents
docker compose up --build                                      # API + Postgres on :8000
pytest
```

## Honest note on the resume numbers
The repo includes the pipeline and measurement hooks. The 3,000+ preference pairs, 1,200+ incident
set, 84% accuracy and 38->24 min fix time must come from your own data: `/metrics` and `eval.py`
compute them. Only claim figures you can reproduce.
