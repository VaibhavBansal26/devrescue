"""DPO fine-tuning with LoRA adapters.

    python -m devrescue.train_dpo --data data/pairs.jsonl --out artifacts/dpo-lora
"""
import argparse

import torch
from datasets import Dataset
from peft import LoraConfig
from transformers import AutoModelForCausalLM, AutoTokenizer
from trl import DPOConfig, DPOTrainer

from .config import BASE_MODEL
from .data import load_pairs, split, to_chat


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", required=True)
    ap.add_argument("--out", default="artifacts/dpo-lora")
    ap.add_argument("--base", default=BASE_MODEL)
    ap.add_argument("--epochs", type=float, default=2)
    ap.add_argument("--lr", type=float, default=5e-6)
    ap.add_argument("--beta", type=float, default=0.1)
    ap.add_argument("--batch", type=int, default=2)
    ap.add_argument("--accum", type=int, default=8)
    ap.add_argument("--max_len", type=int, default=1536)
    ap.add_argument("--max_steps", type=int, default=-1)
    a = ap.parse_args()

    train_rows, eval_rows = split(load_pairs(a.data))
    train_ds, eval_ds = Dataset.from_list(to_chat(train_rows)), Dataset.from_list(to_chat(eval_rows))

    tok = AutoTokenizer.from_pretrained(a.base)
    if tok.pad_token is None:
        tok.pad_token = tok.eos_token
    dtype = torch.bfloat16 if torch.cuda.is_available() else torch.float32
    model = AutoModelForCausalLM.from_pretrained(a.base, torch_dtype=dtype)

    lora = LoraConfig(
        r=16, lora_alpha=32, lora_dropout=0.05, task_type="CAUSAL_LM",
        target_modules=["q_proj", "k_proj", "v_proj", "o_proj"],
    )
    cfg = DPOConfig(
        output_dir=a.out,
        beta=a.beta,
        learning_rate=a.lr,
        num_train_epochs=a.epochs,
        per_device_train_batch_size=a.batch,
        gradient_accumulation_steps=a.accum,
        max_length=a.max_len,
        eval_strategy="epoch",
        save_strategy="epoch",
        logging_steps=10,
        bf16=torch.cuda.is_available(),
        max_steps=a.max_steps,
        report_to="none",
    )
    # With peft_config and no ref_model, TRL uses the adapter-disabled model as reference.
    trainer = DPOTrainer(
        model=model, args=cfg, train_dataset=train_ds, eval_dataset=eval_ds,
        processing_class=tok, peft_config=lora,
    )
    trainer.train()
    trainer.save_model(a.out)
    tok.save_pretrained(a.out)


if __name__ == "__main__":
    main()
