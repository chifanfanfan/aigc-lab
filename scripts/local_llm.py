"""本地部署开源模型 + 推理（Qwen2.5-1.5B-Instruct，GPU）。

    python local_llm.py --model D:/AI/models/Qwen2.5-1.5B-Instruct --prompt "用一句话解释什么是 LoRA"

测三件事：能不能本地跑、显存占多少、生成速度多少 tokens/s。
"""

from __future__ import annotations

import argparse
import time

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True, help="本地模型目录")
    ap.add_argument("--prompt", default="用一句话解释什么是 LoRA。")
    ap.add_argument("--max-new", type=int, default=120)
    ap.add_argument("--device", default="cuda")
    args = ap.parse_args()

    print(f"加载模型: {args.model}")
    t0 = time.time()

    tok = AutoTokenizer.from_pretrained(args.model, trust_remote_code=True)
    model = AutoModelForCausalLM.from_pretrained(
        args.model,
        torch_dtype=torch.float16 if args.device == "cuda" else torch.float32,
        device_map=args.device,
        trust_remote_code=True,
    )
    model.eval()
    load_s = time.time() - t0

    vram = torch.cuda.memory_allocated() / 1e9 if args.device == "cuda" else 0
    print(f"加载耗时 {load_s:.1f}s | 模型占显存 {vram:.2f} GB")

    messages = [{"role": "user", "content": args.prompt}]
    text = tok.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
    ids = tok(text, return_tensors="pt").to(model.device)

    print(f"\n提问: {args.prompt}")
    t1 = time.time()
    with torch.no_grad():
        out = model.generate(
            **ids,
            max_new_tokens=args.max_new,
            do_sample=False,
            temperature=None,
            top_p=None,
            pad_token_id=tok.eos_token_id,
        )
    gen_s = time.time() - t1

    new_tokens = out.shape[1] - ids["input_ids"].shape[1]
    answer = tok.decode(out[0][ids["input_ids"].shape[1]:], skip_special_tokens=True)

    print(f"回答: {answer.strip()}")
    print(f"\n生成 {new_tokens} tokens，耗时 {gen_s:.1f}s → {new_tokens/gen_s:.1f} tokens/s")
    if args.device == "cuda":
        print(f"峰值显存 {torch.cuda.max_memory_allocated()/1e9:.2f} GB")


if __name__ == "__main__":
    main()
