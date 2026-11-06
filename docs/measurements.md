# 实测记录（2026-11-05）

## 环境

| 项 | 值 |
|---|---|
| 显卡 | NVIDIA GeForce RTX 3050 Laptop GPU |
| 显存 | 4 GB |
| 驱动 | 561.09（支持到 CUDA 12.6） |
| 系统 | Windows 11 |
| ComfyUI | v0.44.0 便携版 **cu126** |
| torch | 2.14.1+cu126 |

## 核心数据：GPU 出图 4.6 秒/张

512×512 / 20 步 / euler / cfg 7，同一提示词连跑：

| 次 | 耗时 | 说明 |
|---|---|---|
| 第 1 张 | **12.5 秒** | 含模型加载（只在第一次） |
| 第 2 张 | **4.5 秒** | 稳定速度 |
| 第 3 张 | **4.5 秒** | |
| 第 4 张 | **4.8 秒** | |
| **稳定值** | **≈ 4.6 秒/张** | 50 张约 4 分钟 |

对比 CPU 模式：384×384 / 6 步 = **39 秒**（分辨率低、步数少，还慢 8 倍）。
### 批量 10 张（真实测试）

```
提示词 10 条 | 文本节点 6 | 采样节点 3 | 输出 out_gpu10
  [1/10]  12.2s   ← 含模型加载
  [2/10]   4.5s
  [3/10]   4.9s
  [4/10]   4.5s
  [5/10]   4.5s
  [6/10]   4.9s
  [7/10]   4.5s
  [8/10]   4.5s
  [9/10]   4.8s
  [10/10]  4.5s
完成 10 张，失败 0 张，总耗时 0.9 分钟，平均 5.4 秒/张
```

**结论**：首张 12.2 秒（加载模型），后续稳定 **4.5–4.9 秒**。
按这个速度，**100 张图约 8 分钟**，一条 30 秒短视频的素材批量完全够用。

## 踩坑 1：cu130 版本启动即崩

先下的是 `ComfyUI_windows_portable_nvidia.7z`，自带 **torch 2.14.1+cu130**（CUDA 13.0）。

```
Windows fatal exception: access violation
  torch/cuda/__init__.py, line 591 in _lazy_init
```

诊断：

```powershell
python_embeded\python.exe -c "import torch; print(torch.__version__, torch.version.cuda)"
# → 2.14.1+cu130  13.0

# 驱动版本（注册表 DriverVersion = 32.0.15.6109 → NVIDIA 561.09 → 最高 CUDA 12.6）
```

CUDA 13.0 需要驱动 ≥ 580，机器上是 561.09 → 不匹配。

**解**：换 `ComfyUI_windows_portable_nvidia_cu126.7z`（1.9 GB）。

## 踩坑 2：GPU 被禁用，CUDA 完全不存在

换 cu126 后仍然报：

```
RuntimeError: No CUDA GPUs are available
CUDA not available on this system
```

**不是驱动问题，是显卡被禁用了**：

```powershell
pnputil /enum-devices /class Display
# NVIDIA GeForce RTX 3050 Laptop GPU   Status: Disabled   ← 这里
# AMD Radeon(TM) Graphics              Status: Started
```

修复（需要管理员）：

```
设备管理器 → 显示适配器 → NVIDIA GeForce RTX 3050 Laptop GPU
→ 右键 → 启用设备
```

启用后 `nvidia-smi` 正常，ComfyUI 启动日志出现：

```
Total VRAM 4096 MB, total RAM 15557 MB
Device: cuda:0 NVIDIA GeForce RTX 3050 Laptop GPU : cudaMallocAsync
Enabled pinned memory 6222.0
```

> 这个坑值得记住：**"没有显卡驱动"和"显卡被禁用"报错很像**，
> 但 `pnputil /enum-devices` 一眼能看出 Status 是 Disabled 还是 Started。

## 自定义节点验证

```
/object_info 共 1038 个节点
✅ PromptFromFile   | 分类 custom/batch | 输入 file_path, index
✅ SaveNameByIndex  | 分类 custom/batch | 输入 prefix, index
```

## 批量脚本验证

```
提示词 2 条 | 文本节点 6 | 采样节点 3 | 输出 out_batch
  [1/2]  34.7s  a photo of a ceramic coffee mug...
  [2/2]  43.3s  a leather backpack on a concrete floor...
完成 2 张，失败 0 张，总耗时 1.3 分钟，平均 39.0 秒/张
```

（这是 CPU 模式的数据，GPU 模式按 4.6 秒/张算，50 张约 4 分钟）

## 4 GB 显存的参数建议

| 参数 | 建议值 | 原因 |
|---|---|---|
| 分辨率 | 512×512 | SD1.5 原生，再大容易爆显存 |
| steps | 20 | 再高收益很小 |
| batch_size | 1 | 4 GB 只能 1 |
| 模型 | SD1.5 | SDXL 至少要 8–10 GB |
| 启动参数 | 默认 | 真 OOM 再加 `--lowvram` |

## 已知的画面问题

SD1.5 在「杯子」这类物体上会画出两个把手——这是模型本身的问题，不是参数错。
换更好的底模（如 Realistic Vision、DreamShaper）或加负面提示词能缓解。
