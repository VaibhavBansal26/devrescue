import os
from functools import lru_cache

from .config import ADAPTER_DIR, BASE_MODEL, SYSTEM_PROMPT, build_prompt


@lru_cache(maxsize=1)
def _load():
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer

    tok = AutoTokenizer.from_pretrained(BASE_MODEL)
    model = AutoModelForCausalLM.from_pretrained(
        BASE_MODEL, torch_dtype=torch.bfloat16 if torch.cuda.is_available() else torch.float32
    )
    if os.path.isdir(ADAPTER_DIR):
        from peft import PeftModel

        model = PeftModel.from_pretrained(model, ADAPTER_DIR)
    return tok, model.eval()


def diagnose(kind: str, text: str, max_new_tokens: int = 400) -> str:
    import torch

    tok, model = _load()
    msgs = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": build_prompt(kind, text)},
    ]
    ids = tok.apply_chat_template(msgs, add_generation_prompt=True, return_tensors="pt").to(model.device)
    with torch.no_grad():
        out = model.generate(ids, max_new_tokens=max_new_tokens, do_sample=False)
    return tok.decode(out[0, ids.shape[1]:], skip_special_tokens=True).strip()
