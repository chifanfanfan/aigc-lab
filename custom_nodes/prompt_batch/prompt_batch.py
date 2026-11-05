"""ComfyUI 自定义节点：从文本文件按序号取提示词。

用途：配合 scripts/batch_run.py 做批量出图——脚本每次换 index，
节点返回第 N 行提示词，工作流不用改。

放置位置：
    ComfyUI/custom_nodes/prompt_batch/
        __init__.py
        prompt_batch.py

重启 ComfyUI 后，节点面板里搜 "Prompt From File" 就能找到，
分类在 custom/batch 下面。
"""

from __future__ import annotations

from pathlib import Path


class PromptFromFile:
    """读取 prompts.txt，返回第 index 行（循环取）。"""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "file_path": ("STRING", {"default": "prompts.txt"}),
                "index": ("INT", {"default": 0, "min": 0, "max": 1_000_000, "step": 1}),
            }
        }

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("prompt",)
    FUNCTION = "get_prompt"
    CATEGORY = "custom/batch"

    def get_prompt(self, file_path: str, index: int) -> tuple[str]:
        path = Path(file_path)
        if not path.is_absolute():
            # 相对路径以 ComfyUI 根目录为基准
            path = Path(__file__).resolve().parents[3] / file_path
        if not path.exists():
            return ("",)
        lines = [
            line.strip()
            for line in path.read_text(encoding="utf-8").splitlines()
            if line.strip() and not line.strip().startswith("#")
        ]
        if not lines:
            return ("",)
        return (lines[index % len(lines)],)


class SaveNameByIndex:
    """给保存节点生成带序号的文件名前缀，方便批量归档。"""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "prefix": ("STRING", {"default": "batch"}),
                "index": ("INT", {"default": 0, "min": 0, "max": 1_000_000, "step": 1}),
            }
        }

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("filename_prefix",)
    FUNCTION = "build"
    CATEGORY = "custom/batch"

    def build(self, prefix: str, index: int) -> tuple[str]:
        return (f"{prefix}_{index:04d}",)


NODE_CLASS_MAPPINGS = {
    "PromptFromFile": PromptFromFile,
    "SaveNameByIndex": SaveNameByIndex,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "PromptFromFile": "Prompt From File (batch)",
    "SaveNameByIndex": "Save Name By Index (batch)",
}
