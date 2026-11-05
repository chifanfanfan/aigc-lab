# 实测记录（2026-11-05）

## 环境

| 项 | 值 |
|---|---|
| 显卡 | NVIDIA GeForce RTX 3050 Laptop GPU |
| 显存 | 4 GB |
| 驱动 | 561.09（支持到 CUDA 12.6） |
| 系统 | Windows 11 |
| ComfyUI | v0.44.0 便携版 **cu126** |

## 踩坑：cu130 版本启动即崩

先下的是 `ComfyUI_windows_portable_nvidia.7z`，自带 **torch 2.14.1+cu130**（CUDA 13.0）。
启动直接崩：

```
Windows fatal exception: access violation
Stack:
  torch/cuda/__init__.py, line 591 in _lazy_init
  comfy/model_management.py, line 213 in get_torch_device
```

诊断过程：

```powershell
# 1. 看 torch 要哪个 CUDA
python_embeded\python.exe -c "import torch; print(torch.__version__, torch.version.cuda)"
# → 2.14.1+cu130  13.0

# 2. 看驱动支持到哪个 CUDA
# 注册表 DriverVersion = 32.0.15.6109  → NVIDIA 561.09  → 最高 CUDA 12.6
```

**结论**：CUDA 13.0 运行时需要驱动 ≥ 580，而机器上是 561.09 → 版本不匹配，CUDA 初始化崩溃。

**两个解**：

| 方案 | 代价 | 效果 |
|---|---|---|
| A. 更新显卡驱动到 580+ | 要管理员 + 重启 | 一劳永逸，推荐 |
| B. 换 `ComfyUI_windows_portable_nvidia_cu126.7z` | 重下 1.9 GB | 立刻能用 |

本次采用 **B**，下载 + 解压约 6 分钟。

## 验证结果

| 项 | 结果 |
|---|---|
| ComfyUI 启动（CPU 模式） | ✅ 85 秒起服务，8188 监听 |
| 自定义节点 `PromptFromFile` | ✅ 已注册，分类 `custom/batch` |
| 自定义节点 `SaveNameByIndex` | ✅ 已注册 |
| 节点总数 | 1038（含我们的 2 个） |
| API 单张出图（384×384，6 步） | ✅ 39.1 秒 |
| 批量脚本 2 张 | ✅ 34.7s + 43.3s，平均 39.0 秒/张 |
| 输出图片 | 384×384 RGB PNG，215–285 KB |

> 以上全部是 **CPU 模式**数据。GPU 模式未测（见下）。

## 为什么没测 GPU

这个环境的进程拿不到 GPU 设备（沙箱限制）：

```
nvidia-smi → "NVIDIA-SMI has failed because you do not have suffient permissions"
torch.cuda.is_available() → False
```

所以**GPU 下的真实速度需要本机双击 `run_nvidia_gpu.bat` 验证**。
按 3050 4GB 的经验值预估：SD1.5 512×512 / 20 步约 **8–15 秒/张**。

## GPU 模式的启动方式

```powershell
D:\AI\ComfyUI_cu126\run_nvidia_gpu.bat
```

浏览器 → `http://127.0.0.1:8188`

如果还是崩，说明驱动确实太旧，去 nvidia.cn 更新到 580 以上再试。

## 4 GB 显存的参数建议

| 参数 | 建议值 | 原因 |
|---|---|---|
| 分辨率 | 512×512 | SD1.5 原生，再大就爆显存 |
| steps | 20 | 再高收益很小 |
| batch_size | 1 | 4GB 只能 1 |
| 模型 | SD1.5 | SDXL 至少要 8–10 GB |
| 启动参数 | 默认即可 | 真 OOM 再加 `--lowvram` |
