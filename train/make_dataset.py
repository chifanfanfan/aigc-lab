"""生成一套 LoRA 训练素材：统一风格 + 逐张 captions。

用途：手头没有现成素材时，先用 ComfyUI 批量生成一批同风格图，
跑通 LoRA 训练流程；有真实素材后再替换。

    python train/make_dataset.py --n 20 --out dataset_style

产出：
    dataset_style/
        img_001.png
        img_001.txt   ← "skyshop style, a photo of a ceramic mug, studio light"
        ...

训练时用 skyshop style 作为触发词。
"""

from __future__ import annotations

import argparse
import json
import time
import urllib.parse
import urllib.request
from pathlib import Path

SERVER = "http://127.0.0.1:8188"

# 风格触发词：训练后用它就能召唤这个风格
TRIGGER = "skyshop style"
STYLE = "product photo, soft studio lighting, pastel gradient background, minimalist, high detail, sharp focus"

SUBJECTS = [
    "a ceramic mug",
    "a glass water bottle",
    "a pair of wireless earbuds",
    "a leather tote bag",
    "a bottle of perfume",
    "a wrist watch",
    "a desk lamp",
    "a small potted plant",
    "a notebook and pen",
    "a pair of sunglasses",
    "a stainless steel thermos",
    "a box of tea",
    "a candle in a glass jar",
    "a smartphone",
    "a pair of running shoes",
    "a wooden cutting board",
    "a coffee grinder",
    "a ceramic vase",
    "a backpack",
    "a set of ceramic bowls",
]


def http_json(url: str, payload: dict | None = None, timeout: int = 30) -> dict:
    data = json.dumps(payload).encode() if payload is not None else None
    headers = {"Content-Type": "application/json"} if payload is not None else {}
    req = urllib.request.Request(url, data=data, headers=headers)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read() or b"{}")


def build_workflow(subject: str, seed: int) -> dict:
    """基于 workflows/txt2img_api.json 改提示词和种子。"""
    root = Path(__file__).resolve().parent.parent
    wf = json.loads((root / "workflows" / "txt2img_api.json").read_text("utf-8"))
    wf["6"]["inputs"]["text"] = f"{TRIGGER}, {subject}, {STYLE}"
    wf["7"]["inputs"]["text"] = "blurry, low quality, watermark, text, deformed, extra limbs"
    wf["3"]["inputs"]["seed"] = seed
    return wf


def main() -> None:
    global SERVER

    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=20)
    ap.add_argument("--out", default="dataset_style")
    ap.add_argument("--server", default=SERVER)
    args = ap.parse_args()

    SERVER = args.server.rstrip("/")

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    subjects = (SUBJECTS * ((args.n // len(SUBJECTS)) + 1))[: args.n]
    print(f"生成 {args.n} 张到 {out}/ | 触发词: {TRIGGER}")

    started = time.time()
    ok = 0
    for i, subject in enumerate(subjects, 1):
        wf = build_workflow(subject, seed=7000 + i)
        try:
            t0 = time.time()
            res = http_json(f"{SERVER}/prompt", {"prompt": wf})
            pid = res["prompt_id"]

            hist = {}
            while pid not in hist:
                hist = http_json(f"{SERVER}/history/{pid}")
                if time.time() - t0 > 120:
                    raise TimeoutError("单张超时")
                time.sleep(0.5)

            images = [img for node in hist[pid]["outputs"].values() for img in node.get("images", [])]
            if not images:
                raise RuntimeError("没有输出图")

            img = images[0]
            url = f"{SERVER}/view?filename={urllib.parse.quote(img['filename'])}&subfolder=&type=output"
            png = out / f"img_{i:03d}.png"
            png.write_bytes(urllib.request.urlopen(url, timeout=60).read())

            # 标签：内容 + 触发词 + 风格词
            caption = f"{TRIGGER}, {subject}, {STYLE}"
            (out / f"img_{i:03d}.txt").write_text(caption, "utf-8")

            ok += 1
            print(f"  [{i}/{args.n}] {time.time()-t0:4.1f}s  {subject}")
        except Exception as exc:  # noqa: BLE001
            print(f"  [{i}/{args.n}] 失败：{type(exc).__name__} {exc}")

    print(f"\n完成 {ok} 张，总耗时 {(time.time()-started)/60:.1f} 分钟")


if __name__ == "__main__":
    main()
