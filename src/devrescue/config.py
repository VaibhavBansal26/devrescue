import os

BASE_MODEL = os.getenv("DEVRESCUE_BASE_MODEL", "Qwen/Qwen2.5-0.5B-Instruct")
ADAPTER_DIR = os.getenv("DEVRESCUE_ADAPTER_DIR", "artifacts/dpo-lora")
DATABASE_URL = os.getenv(
    "DATABASE_URL", "postgresql+psycopg2://devrescue:devrescue@localhost:5432/devrescue"
)
SYSTEM_PROMPT = (
    "You are DevRescue, a troubleshooting assistant. Given logs, stack traces or "
    "CI/CD failures, state the most likely ROOT CAUSE first, then give a concise, "
    "ordered FIX. Do not guess beyond the evidence."
)


def build_prompt(kind: str, text: str) -> str:
    """kind: log | stack_trace | ci_failure"""
    return f"[{kind}]\n{text.strip()}"
