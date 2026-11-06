# aigc-lab

AIGC 应用实战：ComfyUI 工作流 + 自定义节点 + 批量出图 + SD1.5 LoRA 训练 + Docker 部署。

对应岗位要求：ComfyUI 工作流搭建 / Stable Diffusion 与 LoRA / Linux 部署 / 本地 GPU 推理。

## 状态（2026-11-05 实测）

| 项 | 状态 |
|---|---|
| ComfyUI 启动（v0.44.0 · cu126 · RTX 3050 4GB） | ✅ 已验证 |
| 自定义节点注册（`PromptFromFile` / `SaveNameByIndex`） | ✅ 已验证（`/object_info` 可查） |
| **GPU 出图 512×512 / 20 步** | ✅ **≈ 4.6 秒/张**（4.5 / 4.5 / 4.8） |
| 首张（含模型加载） | ✅ 12.5 秒 |
| **批量 10 张（GPU）** | ✅ **总耗时 54 秒，平均 5.4 秒/张**，0 失败 |
| SD1.5 LoRA 训练 | ⏳ 待跑（Kaggle notebook 已备好） |
| Docker 部署 | ⏳ 待验证（本机 WSL2 不可用，走 CI） |

> 50 张图 ≈ 4 分钟。CPU 模式下 384×384 / 6 步就要 39 秒，差 8 倍。

## 目录

```
custom_nodes/prompt_batch/   自定义节点：从文件按序号取提示词 + 生成带序号的文件名
scripts/batch_run.py         批量出图：调 ComfyUI HTTP API，串行跑 N 条提示词
scripts/check_env.ps1        环境自检：显卡/显存/Python/磁盘
workflows/txt2img_api.json   可直接用的 API 格式工作流（文生图）
train/kohya_sd15_lora.toml   SD1.5 LoRA 训练配置（kohya_ss，4G 极限档）
train/kaggle_sd15_lora.ipynb  Kaggle 免费 T4 训练 notebook（本机显存不够时用）
docker/Dockerfile            ComfyUI 的 GPU 镜像
docs/measurements.md         实测数据 + cu130 驱动不匹配的排查过程
docs/hardware.md             4 GB 显存的边界与云端降级方案
samples/                     CPU 模式跑出来的两张图（6 步，比较糊，仅证明链路通）
```

## 快速开始

### 0. 自检

```powershell
powershell -ExecutionPolicy Bypass -File scripts\check_env.ps1
```

### 1. ComfyUI

```powershell
run_nvidia_gpu.bat        # GPU 模式
```

浏览器打开 `http://127.0.0.1:8188`。

> **驱动必须 ≥ 580**，否则要用 `cu126` 版本的便携包。
> 本机驱动 561.09，所以用的是 cu126 包（详见 docs/measurements.md）。

### 2. 装自定义节点

```powershell
xcopy /E /I custom_nodes\prompt_batch <ComfyUI目录>\custom_nodes\prompt_batch
```

重启后，节点面板 → `custom/batch` → **Prompt From File (batch)**。

### 3. 批量出图

```powershell
python scripts\batch_run.py --workflow workflows\txt2img_api.json --prompts prompts.txt --out out
```

输出：

```
提示词 10 条 | 文本节点 6 | 采样节点 3 | 输出 out
  [1/10]  34.7s  a photo of a ceramic coffee mug...
  [2/10]  43.3s  a leather backpack on a concrete floor...
完成 2 张，失败 0 张，总耗时 1.3 分钟，平均 39.0 秒/张
```


### 5. LoRA 数据集（可用 AI 生成）

```powershell
python train\make_dataset.py --n 20 --out dataset_style
```

固定风格 + 换 20 个主体，自动生成图和标签（**5.2 秒/张，20 张 1.7 分钟**），
打包成 `dataset_style.zip`（6.3 MB）可直接传 Kaggle。详见 [docs/lora_dataset.md](docs/lora_dataset.md)。

### 6. 训 LoRA（上云）

本机 4 GB 显存训不动，用 `train/kaggle_sd15_lora.ipynb` 上 Kaggle 免费 T4 跑。

## 踩过的坑

1. **cu130 版本启动即崩**：torch 2.14.1+cu130 需要驱动 ≥ 580，本机 561.09
   → `Windows fatal exception: access violation` in `torch.cuda._lazy_init`
2. **`batch_run.py` 的 `global` 声明位置错误**：`default=SERVER` 在 `global SERVER` 之前用到了它
   → `SyntaxError: name 'SERVER' is used prior to global declaration`，把 `global` 提到函数第一行
3. **提示词文件带 BOM**：第一条提示词前面多了不可见字符
   → 读取时用 `utf-8-sig`

## 下一步

- [ ] 本机 GPU 模式跑一张 512×512，记录真实耗时
- [ ] Kaggle 训一个 LoRA，下载后做 base vs LoRA 对比
- [ ] Docker 镜像在 Codespaces 上验证构建
