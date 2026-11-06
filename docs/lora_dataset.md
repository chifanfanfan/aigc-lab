# LoRA 数据集怎么做

## 一、先明确：为什么要训 LoRA

LoRA（Low-Rank Adaptation）是在不改变底模的情况下，让模型学会**一个特定风格/主体**。

用途举例：

| 场景 | 训练目标 |
|---|---|
| 电商 | 让所有商品图统一成品牌视觉风格 |
| 人像 | 让模型学会某个人的脸（需真人授权） |
| 插画 | 复刻某种画风 |
| 产品 | 让模型稳定生成某个具体产品（需多角度素材） |

## 二、数量要求

| 类型 | 最少 | 推荐 | 说明 |
|---|---|---|---|
| 画风 | 15 张 | 30–60 张 | 张数少但风格要一致 |
| 主体/人物 | 20 张 | 30–100 张 | 需要多角度、多表情 |
| 产品 | 20 张 | 50+ 张 | 需要不同背景/角度 |

**少于 15 张基本训不出效果**，容易过拟合（只会复现训练图）。

## 三、数据集结构

```
train_data/
  img_001.png
  img_001.txt     ← 文件名必须一一对应
  img_002.png
  img_002.txt
  ...
```

**标签（.txt）写什么**：

```
skyshop style, a ceramic mug, product photo, soft studio lighting, pastel background
└─ 触发词 ─┘  └─ 内容 ──┘  └────────── 风格描述 ──────────┘
```

三条规则：

1. **触发词要罕见**：`skyshop style` / `sks` / `ohwx` 这种模型没见过的词，才会被"绑定"到新概念
2. **内容写清楚**：主体是什么，避免模型把主体和风格混淆
3. **风格词固定**：所有图用同一套风格词，模型才会学到"这个词 = 这个风格"

## 四、本仓库的做法：用 ComfyUI 自己生成素材

```powershell
python train/make_dataset.py --n 20 --out dataset_style
```

它会：

- 用固定风格提示词（`product photo, soft studio lighting, pastel gradient background...`）
- 换 20 个不同主体（杯子、耳机、香水、手表…）
- 每张自动生成对应 `.txt` 标签
- 全部走 ComfyUI 的 HTTP API，**平均 5.2 秒/张，20 张 1.7 分钟**

**实测结果**：风格一致性不错（渐变背景、柔光、居中构图），可以直接拿去训练。

产物：

```
dataset_style/     20 张 png + 20 个 txt
dataset_style.zip  6.3 MB，可直接传 Kaggle
```

> 说明：用 AI 生成的图训 LoRA 是"风格蒸馏"，适合跑通流程和做风格迁移。
> **如果是电商真实业务，优先用真实商品图**——真实素材的细节是生成图替代不了的。

## 五、上传 Kaggle 并训练

1. Kaggle → Datasets → **New Dataset**
2. 上传 `dataset_style.zip`，名字填 `lora-data`
3. 打开 `train/kaggle_sd15_lora.ipynb`，按里面的步骤跑
4. 训完在 `/kaggle/working/lora_out` 下载 `style_demo.safetensors`

## 六、训练参数怎么选（4 GB 显存 vs 16 GB T4）

| 参数 | 本机 4 GB | Kaggle T4 16 GB |
|---|---|---|
| `network_dim` | 8 | **32** |
| `network_alpha` | 4 | **16** |
| `train_batch_size` | 1 | **2** |
| `resolution` | 512 | 512 |
| `gradient_checkpointing` | 必开 | 可开 |
| `cache_latents` | 必开 | 建议开 |
| `max_train_epochs` | 10 | 10 |

**本地 4 GB 想试也行**，但要接受两个后果：慢（可能要 2–3 小时）、可能中途 OOM。

## 七、训完怎么验证

**必须做对比**，否则说不清"有没有用"：

```powershell
# 同一个 prompt、同一个 seed
base:  "a ceramic mug, product photo, soft studio lighting, pastel gradient background"
LoRA:  "skyshop style, a ceramic mug, product photo, soft studio lighting, pastel gradient background"
```

把两张图并排拼起来，这才是能放进简历/面试的"证据"。

## 八、常见问题

| 现象 | 原因 | 处理 |
|---|---|---|
| 训完完全没有效果 | 学习率太低 / epoch 太少 | `lr` 提到 3e-4，`epoch` 到 15 |
| 只会复现训练图 | 过拟合 | 减少 epoch，降低 `network_dim` |
| 画面崩坏/全黑 | 学习率太高 | `lr` 降到 5e-5 |
| 主体和风格混在一起 | 标签没写清内容 | 标签里明确写主体是什么 |
| 触发词在其他图上也生效 | 触发词太常见 | 换更罕见的词 |

## 九、面试怎么讲这段

> "我训 LoRA 的数据集是自己用 ComfyUI 批量生成的：固定风格提示词，换 20 个主体，
> 每张自动配标签，平均 5.2 秒一张，1.7 分钟出完 20 张。
> 训练放在 Kaggle 的免费 T4 上——本机只有 4 GB 显存，`network_dim` 只能开 8。
> 训完我用同一 prompt 和 seed 做了 base vs LoRA 对比。"

**"素材生成 → 自动打标 → 云端训练 → 对比验证"** 是一条完整的工程链路，比"我会训 LoRA"具体得多。
