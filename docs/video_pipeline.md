# 批量出视频（实测）

## 结论

在 **4 GB 显存**的 3050 上，用 **ComfyUI 出图 + ffmpeg 合成**做出 16 秒商品短视频：

| 项 | 值 |
|---|---|
| 输入 | 6 张商品图（ComfyUI 生成） |
| 输出 | `samples/product_video.mp4` |
| 分辨率 | 1080×1080 |
| 帧率 | 30 fps |
| 时长 | 16 秒（每张 3 秒，0.4 秒交叉淡入淡出） |
| 体积 | 2.8 MB |
| 合成耗时 | 约 20 秒（纯 CPU） |

## 为什么不用 AnimateDiff / SVD

| 方案 | 显存需求 | 4 GB 能不能跑 |
|---|---|---|
| **AnimateDiff**（SD1.5 + 运动模块） | 6–8 GB | ❌ 几乎肯定 OOM |
| **SVD**（图生视频） | 10 GB+ | ❌ |
| **图 + ffmpeg 运镜**（本方案） | 0（纯 CPU） | ✅ |

电商批量出片里，「商品图 + 推拉运镜 + 转场 + 字幕」本来就是主流做法——
真正需要"画面里有物体运动"才用 AnimateDiff。

## 实现

### 单张图的运镜（zoompan）

```bash
ffmpeg -loop 1 -i img.png -t 3 \
  -vf "scale=1080:1080:force_original_aspect_ratio=increase,crop=1080:1080,\
zoompan=z='1+0.08*on/90':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d=90:s=1080x1080:fps=30" \
  -c:v libx264 -crf 20 clip.mp4
```

- `z` 从 1.0 线性到 1.08 → 缓慢推近
- 奇数张反转成推远，避免节奏单调
- `d=90` = 3 秒 × 30 fps

### 多段拼接加转场（xfade）

```bash
ffmpeg -i c0.mp4 -i c1.mp4 -i c2.mp4 \
  -filter_complex "[0:v][1:v]xfade=transition=fade:duration=0.4:offset=2.6[v1];\
[v1][2:v]xfade=transition=fade:duration=0.4:offset=5.2[v2]" \
  -map "[v2]" -c:v libx264 -crf 20 out.mp4
```

`offset = i × (segment_seconds - fade)`

## 用法

```powershell
# 1. 装 ffmpeg（用 pip 包，自带二进制，绕过国内下载源问题）
pip install imageio-ffmpeg

# 2. 合成
python scripts/make_video.py --images out_video --out samples/product_video.mp4 --seconds 3 --limit 6
```

脚本会自动找 ffmpeg：先找 PATH 里的，找不到就用 `imageio-ffmpeg` 自带的。

## 踩坑

| 问题 | 现象 | 解决 |
|---|---|---|
| ffmpeg 下载源全被墙 | gyan.dev / GitHub 都超时 | 用 `imageio-ffmpeg` pip 包，自带二进制 |
| venv 里 pip 卡死 | 10 分钟没动静 | 换 ComfyUI 自带 python 装（2 分钟） |
| **GPU 降频** | 单张从 4.5 秒掉到 180 秒 | 显卡 86°C 触发热降频，`nvidia-smi` 看 `clocks.sm` 只有 1890/2100 MHz |

## 面试怎么讲

> "视频这块我做的是「图 + 运镜 + 转场」的批量管线，不是 AnimateDiff——
> 因为我笔记本只有 4 GB 显存，AnimateDiff 至少 6–8 GB，跑不动。
> 但电商批量出片本来就是这个方案：ComfyUI 批量出商品图，ffmpeg 的 zoompan 做推拉，
> xfade 做转场，6 张图 20 秒合成一条 16 秒的 1080p 视频。
> 真要物体运动，得上 AnimateDiff 或 SVD，那需要 12 GB 以上的卡。"

**主动讲清"为什么不用 AI 视频模型"，比硬吹会做更有说服力。**
