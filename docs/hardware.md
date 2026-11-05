# 硬件实测与降级方案

## 本机配置（2026-11 实测）

| 项 | 值 |
|---|---|
| 显卡 | **NVIDIA GeForce RTX 3050 Laptop GPU** |
| 显存 | **4 GB** |
| 集显 | AMD Radeon (0.5 GB，跑 ComfyUI 用不上) |
| Python | 3.13.17 |
| 磁盘 | C: 34.5 GB / D: 18.0 GB 可用 |
| 系统 | Windows 11（Docker/WSL2 装不上，见 kb-bot 第 19 章） |

## 4 GB 显存能做什么

| 任务 | 可行性 | 说明 |
|---|---|---|
| SD1.5 出图（512×512，20 steps） | ✅ 可以 | 约 15–40 秒/张，批量跑没问题 |
| SDXL 出图 | ❌ 不行 | 至少要 8–10 GB，开 `--lowvram` 也极慢 |
| ComfyUI 自定义节点 + 批量脚本 | ✅ 完全不受限 | 不占显存 |
| Docker 打包 ComfyUI | ⚠️ 本机起不来 | WSL2 装不上（CBS 0x800f0922），改用 CI / 云端验证 |
| SD1.5 LoRA 训练（network_dim=8, batch=1） | ⚠️ 极限 | 可能 OOM，要开 `gradient_checkpointing + cache_latents + lowram` |
| AnimateDiff / SVD 视频 | ❌ 基本不行 | 视频要 10 GB 以上，或极低分辨率的慢速实验 |

## 结论：拆成「本地做 + 云端训」

```
本地（4 GB 够用）：
  ✅ ComfyUI 出图、自定义节点、批量脚本、参数调优
  ✅ 学会工作流搭建（JD 第 2 条）

云端（免费或几块钱）：
  ✅ SD1.5 LoRA 训练（JD 第 3 条）——Kaggle 免费 T4 16GB，或 AutoDL 约 2 元/小时
  ✅ Docker 部署验证（JD 第 4 条）——Codespaces 或云服务器
  ✅ 视频工作流（JD 第 2 条延伸）
```

## 云端训练：Kaggle（免费）

1. 注册 kaggle.com（邮箱即可，不要信用卡）
2. **Create → New Notebook** → 右侧 Settings：
   - Accelerator: **GPU T4 x2**（免费，每周 30 小时）
   - Internet: **On**
3. 依次跑：

```python
!git clone https://github.com/kohya-ss/sd-scripts
%cd sd-scripts
!pip install -q -r requirements.txt
!accelerate config default
```

```python
# 上传数据集（图片 + 同名 txt 标签）到 /kaggle/working/train_data
!accelerate launch --num_cpu_threads_per_process 2 sdxl_train_network.py \
  --pretrained_model_name_or_path=/kaggle/input/sd15/anything-v5.safetensors \
  --train_data_dir=/kaggle/working/train_data \
  --output_dir=/kaggle/working/out \
  --network_module=networks.lora --network_dim=32 --network_alpha=16 \
  --resolution=512 --train_batch_size=2 --max_train_epochs=10 \
  --learning_rate=1e-4 --optimizer_type=AdamW8bit \
  --mixed_precision=fp16 --save_model_as=safetensors \
  --output_name=style_demo
```

> SD1.5 用 `train_network.py`（不是 `sdxl_train_network.py`）。

4. 训完下载 `style_demo.safetensors`（几十 MB），拷回本地 ComfyUI 的 `models/loras/`

**要留下的证据**：TensorBoard 曲线截图、`safetensors` 文件、同 prompt 的 base vs LoRA 对比图。

## 云端训练：AutoDL（便宜，中文界面）

| 项 | 说明 |
|---|---|
| 价格 | RTX 3090 / 4090 约 1.5–2.5 元/小时 |
| 一次 LoRA 训练 | 约 1 小时，**总花费 2–3 元** |
| 优势 | 有现成的 kohya 镜像，不用自己装环境 |
| 用法 | 注册 → 选 GPU 实例 → 选「kohya_ss」镜像 → 传数据 → 跑 |

## 面试怎么说这段

> "我本地只有 4 GB 显存的 3050，SD1.5 出图没问题，但 LoRA 训练显存不够。
> 所以拆成两部分：工作流和批量脚本在本地做，训练放到 Kaggle 的免费 T4 上跑。
> 这也让我清楚显存和 batch/dim 的关系——4 GB 只能 network_dim=8，16 GB 能上 32。"

**知道自己的硬件边界，并给出替代方案**，比"我全都本地跑"更专业。
