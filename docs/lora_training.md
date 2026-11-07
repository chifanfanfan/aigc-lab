# LoRA 训练全流程（实测）

## 结果

![base vs LoRA](samples/lora_compare.png)

同一个 prompt、同一个 seed（1234），左边是原模型，右边加载了我训的 LoRA。

| 项 | 数值 |
|---|---|
| 训练数据 | 20 张 AI 生成的同风格商品图 + 自动标签 |
| 底模 | SD 1.5（v1-5-pruned-emaonly） |
| 训练步数 | 1000 步（20 张 × 10 重复 × 10 epoch） |
| **耗时** | **19 分 15 秒** |
| **速度** | **1.16 秒/步**（Tesla T4 16 GB） |
| **loss** | 0.18 → **0.069** |
| 模型大小 | **36 MB**（`network_dim=32`） |
| 平台 | Kaggle 免费 T4（每周 30 小时额度） |

## 训练参数

```bash
python train_network.py \
  --pretrained_model_name_or_path=/kaggle/working/models/sd15.safetensors \
  --train_data_dir=/kaggle/working/train_data \
  --output_dir=/kaggle/working/lora_out \
  --output_name=style_demo \
  --network_module=networks.lora \
  --network_dim=32 --network_alpha=16 \
  --resolution=512,512 --train_batch_size=2 --max_train_epochs=10 \
  --learning_rate=1e-4 --text_encoder_lr=5e-5 --unet_lr=1e-4 \
  --optimizer_type=AdamW8bit --lr_scheduler=cosine --lr_warmup_steps=50 \
  --mixed_precision=fp16 --save_precision=fp16 --save_model_as=safetensors \
  --cache_latents --gradient_checkpointing --sdpa --seed=42 --caption_extension=.txt
```

> 关键：**用 `python` 直接跑，不要用 `accelerate launch`**。
> Kaggle 给的是双卡（T4 x2），accelerate 会起 2 个进程，第二个挂了会把第一个带崩（`ChildFailedError`）。

## 数据集结构（kohya 要求）

```
train_data/
└── 10_style/          ← 文件夹名 = 重复次数_名字，不能直接放图片
    ├── img_001.png
    ├── img_001.txt
    └── ...
```

标签内容：

```
skyshop style, a ceramic mug, product photo, soft studio lighting, pastel gradient background
└─ 触发词 ─┘  └─ 内容 ─┘  └──────────────── 风格 ────────────────┘
```

## 对比方法

```powershell
python scripts/lora_compare.py \
  --prompt "a ceramic mug, product photo, soft studio lighting, pastel gradient background" \
  --lora style_demo.safetensors --seed 1234 --strength 0.9 \
  --out samples/lora_compare.png
```

脚本会：跑 base → 插入 `LoraLoader` 节点跑 LoRA → 下载两张图 → 拼成左右对比图。

实测耗时：base 10.1 秒，LoRA 7.1 秒（第二张更快是因为模型已在显存里）。

## 踩坑清单（这一路踩的）

| # | 问题 | 现象 | 解决 |
|---|---|---|---|
| 1 | **ComfyUI cu130 版启动崩** | `Windows fatal exception: access violation` in `torch.cuda._lazy_init` | torch 2.14+cu130 要驱动 ≥580，本机 561.09 → 换 **cu126** 版 |
| 2 | **显卡被禁用** | `RuntimeError: No CUDA GPUs are available` | `pnputil /enum-devices /class Display` 看到 `Status: Disabled` → 设备管理器启用 |
| 3 | **Kaggle 数据集不挂载** | `/kaggle/input` 为空 | 数据集只在 **session 启动时**挂载 → 必须停 session 再启动 |
| 4 | **Kaggle 自动解压 zip** | 搜 `*.zip` 找不到 | 文件被展开成 png，直接搜 `**/*.png` |
| 5 | **kohya 报 No data found** | `train_data_dir must be the parent of folders with images` | 目录要 `train_data/10_style/图片`，不能直接放图 |
| 6 | **accelerate 双卡崩** | `ChildFailedError`，rank 1 exitcode 1 | 改单进程 `python train_network.py` |
| 7 | **pip 重装 torch 卡 2 小时** | session 超时断开，文件全丢 | `grep -v torch requirements.txt` 过滤，用 Kaggle 自带 torch |
| 8 | **xformers 未装** | 训练启动即报错 | 改用 `--sdpa` |
| 9 | **Kaggle 输出文件拿不出来** | Output 页空的 | Quick Save 不打包工作目录 → 只能 `Save & Run All (Commit)` |
| 10 | **临时文件床踩雷** | 0x0.st 关停、catbox 要 UA、tmpfiles 按钮是广告 | 从页面 HTML 里正则找带签名的真实链接 |

## 面试怎么讲

> "我训了一个 SD1.5 的 LoRA。数据是我用 ComfyUI 批量生成的 20 张同风格商品图，
> 平均 5.2 秒一张，标签脚本自动写。
> 训练放在 Kaggle 免费 T4 上——本机只有 4 GB 显存，rank 只能开到 8。
> 1000 步跑了 19 分钟，loss 从 0.18 降到 0.069，模型 36 MB。
> 训完用同 prompt 同 seed 做了 base vs LoRA 对比，风格迁移很明显。"

**"自己造数据 → 自动打标 → 云端训练 → 对比验证"** 是完整链路，
比"我会训 LoRA"具体得多。
