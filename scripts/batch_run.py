"""批量出图：调 ComfyUI 的 HTTP API，把提示词列表跑成一批图。

前置：
1. ComfyUI 已启动（默认 http://127.0.0.1:8188）
2. 在 ComfyUI 里搭好工作流，用 "Save (API Format)" 导出成 workflow_api.json
   （注意：不是普通的 Save，必须选 API Format）

用法：
    python batch_run.py --workflow workflow_api.json --prompts prompts.txt --out out

脚本会自动找到工作流里的：
- 正向提示词节点（CLIPTextEncode，取第一个）
- KSampler 节点（换 seed）
如果你的工作流结构不同，用 --text-node / --seed-node 指定节点 id。
"""

from __future__ import annotations

import argparse
import json
import time
import urllib.request
from pathlib import Path

SERVER = "http://127.0.0.1:8188"


def http_json(url: str, payload: dict | None = None, timeout: int = 30) -> dict:
    data = None
    headers = {}
    if payload is not None:
        data = json.dumps(payload).encode()
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, headers=headers)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read() or b"{}")


def find_node(workflow: dict, class_type: str) -> str | None:
    for node_id, node in workflow.items():
        if node.get("class_type") == class_type:
            return node_id
    return None


def wait_done(prompt_id: str, timeout: int = 300) -> dict:
    """轮询 /history 直到这个 prompt 出结果。"""
    started = time.time()
    while time.time() - started < timeout:
        hist = http_json(f"{SERVER}/history/{prompt_id}")
        if prompt_id in hist:
            return hist[prompt_id]
        time.sleep(1.5)
    raise TimeoutError(f"出图超时：{prompt_id}")


def download_image(filename: str, subfolder: str, out_dir: Path) -> Path:
    url = f"{SERVER}/view?filename={urllib.parse.quote(filename)}&subfolder={subfolder}&type=output"
    dest = out_dir / filename
    with urllib.request.urlopen(url, timeout=60) as resp, dest.open("wb") as fh:
        fh.write(resp.read())
    return dest


def main() -> None:
    global SERVER

    ap = argparse.ArgumentParser()
    ap.add_argument("--workflow", required=True, help="API 格式的工作流 json")
    ap.add_argument("--prompts", required=True, help="每行一条提示词")
    ap.add_argument("--out", default="out")
    ap.add_argument("--text-node", default=None, help="提示词节点 id（默认自动找第一个 CLIPTextEncode）")
    ap.add_argument("--seed-node", default=None, help="采样器节点 id（默认自动找 KSampler）")
    ap.add_argument("--server", default=SERVER)
    args = ap.parse_args()

    SERVER = args.server.rstrip("/")

    workflow = json.loads(Path(args.workflow).read_text("utf-8"))
    prompts = [
        line.strip()
        for line in Path(args.prompts).read_text("utf-8-sig").splitlines()
        if line.strip() and not line.strip().startswith("#")
    ]
    text_id = args.text_node or find_node(workflow, "CLIPTextEncode")
    seed_id = args.seed_node or find_node(workflow, "KSampler")
    if not text_id or not seed_id:
        raise SystemExit("工作流里找不到 CLIPTextEncode / KSampler，用 --text-node / --seed-node 手动指定")

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    print(f"提示词 {len(prompts)} 条 | 文本节点 {text_id} | 采样节点 {seed_id} | 输出 {out_dir}")

    ok, fail = 0, 0
    started = time.time()
    for i, prompt in enumerate(prompts):
        wf = json.loads(json.dumps(workflow))  # 深拷贝，避免污染模板
        wf[text_id]["inputs"]["text"] = prompt
        wf[seed_id]["inputs"]["seed"] = 1000 + i

        try:
            t0 = time.perf_counter()
            res = http_json(f"{SERVER}/prompt", {"prompt": wf})
            prompt_id = res["prompt_id"]
            hist = wait_done(prompt_id)
            elapsed = time.perf_counter() - t0

            for node_out in hist.get("outputs", {}).values():
                for img in node_out.get("images", []):
                    download_image(img["filename"], img.get("subfolder", ""), out_dir)
            ok += 1
            print(f"  [{i+1}/{len(prompts)}] {elapsed:5.1f}s  {prompt[:40]}")
        except Exception as exc:  # noqa: BLE001
            fail += 1
            print(f"  [{i+1}/{len(prompts)}] 失败：{type(exc).__name__} {exc}")

    total = time.time() - started
    print(f"\n完成 {ok} 张，失败 {fail} 张，总耗时 {total/60:.1f} 分钟，平均 {total/max(ok,1):.1f} 秒/张")


if __name__ == "__main__":
    import urllib.parse

    main()
