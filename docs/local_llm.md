# 本地部署开源模型 + 推理（实测）

## 环境

| 项 | 值 |
|---|---|
| 显卡 | RTX 3050 Laptop，4 GB |
| Python | ComfyUI 自带的 `python_embeded`（torch 2.14.1+cu126，CUDA 可用） |
| 依赖 | transformers 5.21.0 + accelerate 1.15.0（清华镜像装） |
| 模型来源 | `hf-mirror.com`（40+ MB/s） |

## 结果

| 模型 | 大小 | 加载耗时 | 显存占用 | **生成速度** | 状态 |
|---|---|---|---|---|---|
| Qwen2.5-0.5B-Instruct | 942 MB | 9.1 秒 | **1.0 GB** | **3.3–4.3 tokens/s** | ✅ 跑通 |
| Qwen2.5-1.5B-Instruct | 2.94 GB | — | — | — | ❌ 加载失败 |

### 1.5B 失败原因

```
OSError: 页面文件太小，无法完成操作。 (os error 1455)
```

Windows 虚拟内存（页面文件）不够，加载 2.94 GB 的 safetensors 时 mmap 失败。
**解决**：系统属性 → 高级 → 性能设置 → 高级 → 虚拟内存 → 调到 16 GB 以上，重启生效（需要管理员）。

### 0.5B 慢的原因（分析）

3–4 tokens/s 对 0.5B 模型来说偏慢（理论上 3050 上应该有 30+）。

可能原因：
1. **笔记本 GPU 功耗墙 / 电池模式**
2. 4 GB 显存太小，驱动有换页开销
3. transformers 5.x 的 generate 实现没有最优路径（没上 vLLM / llama.cpp）

**改进方向**：换 llama.cpp（GGUF 量化 + KV cache 优化）或 vLLM，速度能提升一个量级。

## 复现

```powershell
# 1. 装依赖（用 ComfyUI 自带 python，省去装 torch）
D:\AI\ComfyUI_cu126\python_embeded\python.exe -m pip install transformers accelerate safetensors -i https://pypi.tuna.tsinghua.edu.cn/simple

# 2. 下模型
$env:HF_ENDPOINT='https://hf-mirror.com'
python -c "from huggingface_hub import snapshot_download; snapshot_download('Qwen/Qwen2.5-0.5B-Instruct', local_dir=r'D:\AI\models\Qwen2.5-0.5B-Instruct')"

# 3. 推理
python scripts/local_llm.py --model D:\AI\models\Qwen2.5-0.5B-Instruct --prompt "用一句话解释什么是 LoRA。"
```

## 面试怎么讲（诚实版）

> "本地推理我跑通了：用 ComfyUI 自带的 torch 环境加载 Qwen2.5-0.5B，fp16 上 GPU，
> 显存占 1 GB，3–4 tokens/s。
> 1.5B 加载失败，报 Windows 页面文件不足——这个是系统虚拟内存的坑，调大就能跑。
> 速度慢是因为我没上 vLLM 或 llama.cpp，纯 transformers 的 generate 没有 KV cache 优化。"

**主动说出"慢在哪、怎么改"，比报一个漂亮的 token/s 可信。**

## 微调这块的真实情况

| 项 | 在哪做的 | 状态 |
|---|---|---|
| SD1.5 LoRA 训练 | **Kaggle T4（云端）** | ✅ 已完成，1000 步 / 19 分钟 / loss 0.069 |
| 本地微调 | 本机 4 GB | ❌ 显存不够，没做 |

**面试要如实说**：微调在云端做的，本地只做到推理。

> "4 GB 显存训 SD1.5 LoRA 不够（至少要 6 GB），所以训练放在 Kaggle 免费 T4 上，
> 单卡 1.16 秒/步，1000 步 19 分钟。本地负责推理和出图。"
