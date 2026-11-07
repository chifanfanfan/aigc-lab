"""LoRA 对比：同一个 prompt、同一个 seed，跑 base 和加 LoRA 两张，拼成对比图。

    python scripts/lora_compare.py --lora style_demo.safetensors \
        --prompt "a ceramic mug, product photo, soft studio lighting, pastel gradient background" \
        --seed 1234 --out samples/lora_compare.png

前提：ComfyUI 在跑，且 LoRA 已放进 ComfyUI/models/loras/。
"""

from __future__ import annotations

import argparse
import json
import time
import urllib.parse
import urllib.request
from pathlib import Path

SERVER = "http://127.0.0.1:8188"


def http_json(url: str, payload: dict | None = None, timeout: int = 30) -> dict:
    data = json.dumps(payload).encode() if payload is not None else None
    headers = {"Content-Type": "application/json"} if payload is not None else {}
    req = urllib.request.Request(url, data=data, headers=headers)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read() or b"{}")


def build(wf: dict, prompt: str, seed: int, lora: str | None, strength: float) -> dict:
    wf = json.loads(json.dumps(wf))
    wf["3"]["inputs"]["seed"] = seed

    if lora:
        # 插入 LoRA 节点：model/clip 改从它输出
        wf["10"] = {
            "class_type": "LoraLoader",
            "inputs": {
                "model": ["4", 0],
                "clip": ["4", 1],
                "lora_name": lora,
                "strength_model": strength,
                "strength_clip": strength,
            },
        }
        wf["6"]["inputs"]["clip"] = ["10", 1]
        wf["7"]["inputs"]["clip"] = ["10", 1]
        wf["3"]["inputs"]["model"] = ["10", 0]
        wf["6"]["inputs"]["text"] = prompt
    else:
        wf["6"]["inputs"]["text"] = prompt

    return wf


def run(wf: dict, tag: str, out_dir: Path) -> Path:
    res = http_json(f"{SERVER}/prompt", {"prompt": wf})
    pid = res["prompt_id"]
    started = time.time()
    hist = {}
    while pid not in hist:
        hist = http_json(f"{SERVER}/history/{pid}")
        if time.time() - started > 300:
            raise TimeoutError(f"{tag} 出图超时")
        time.sleep(0.5)

    images = [img for node in hist[pid]["outputs"].values() for img in node.get("images", [])]
    if not images:
        raise RuntimeError(f"{tag} 没有输出图")

    img = images[0]
    url = f"{SERVER}/view?filename={urllib.parse.quote(img['filename'])}&subfolder=&type=output"
    dest = out_dir / f"{tag}.png"
    dest.write_bytes(urllib.request.urlopen(url, timeout=60).read())
    print(f"  {tag}: {time.time()-started:5.1f}s  {dest.name}")
    return dest


def main() -> None:
    global SERVER

    ap = argparse.ArgumentParser()
    ap.add_argument("--workflow", default="workflows/txt2img_api.json")
    ap.add_argument("--prompt", required=True)
    ap.add_argument("--lora", required=True, help="LoRA 文件名，如 style_demo.safetensors")
    ap.add_argument("--trigger", default="skyshop style", help="训练时用的触发词")
    ap.add_argument("--seed", type=int, default=1234)
    ap.add_argument("--strength", type=float, default=0.9)
    ap.add_argument("--out", default="samples/lora_compare.png")
    ap.add_argument("--server", default=SERVER)
    args = ap.parse_args()

    SERVER = args.server.rstrip("/")
    root = Path(__file__).resolve().parent.parent
    wf = json.loads((root / args.workflow).read_text("utf-8"))

    out_dir = root / "samples" / "_tmp"
    out_dir.mkdir(parents=True, exist_ok=True)

    print(f"prompt: {args.prompt}\nseed: {args.seed}\nLoRA: {args.lora} (strength {args.strength})")
    base_png = run(build(wf, args.prompt, args.seed, None, args.strength), "base", out_dir)
    lora_png = run(build(wf, f"{args.trigger}, {args.prompt}", args.seed, args.lora, args.strength), "lora", out_dir)

    # 拼成左右对比图
    from PIL import Image, ImageDraw

    a, b = Image.open(base_png), Image.open(lora_png)
    pad, header = 12, 46
    canvas = Image.new("RGB", (a.width + b.width + pad * 3, max(a.height, b.height) + header + pad * 2), "white")
    canvas.paste(a, (pad, header + pad))
    canvas.paste(b, (pad * 2 + a.width, header + pad))
    draw = ImageDraw.Draw(canvas)
    draw.text((pad, 16), f"Base model (seed {args.seed})", fill="black")
    draw.text((pad * 2 + a.width, 16), f"+ LoRA: {args.lora} (seed {args.seed})", fill="black")

    out = root / args.out
    out.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(out)
    print(f"\n对比图: {out}  ({out.stat().st_size/1024:.0f} KB)")


if __name__ == "__main__":
    main()
