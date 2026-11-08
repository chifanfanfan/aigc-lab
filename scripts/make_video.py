"""批量出视频：把一组商品图做成带推拉运镜 + 转场的短视频。

    python scripts/make_video.py --images out/ --out samples/demo.mp4 --seconds 3

依赖 ffmpeg（找不到时会提示安装方式；也支持 imageio-ffmpeg 自带的二进制）。

为什么做这个：
4 GB 显存跑不动 AnimateDiff（需要 6-8 GB），但电商实际业务里
「商品图 + 运镜 + 转场 + 字幕」是最常见的批量出片方式，
用 ffmpeg 的 zoompan + xfade 就能做，显存零压力。
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path


def find_ffmpeg() -> str | None:
    """优先系统 PATH，其次 imageio-ffmpeg 自带的二进制。"""
    exe = shutil.which("ffmpeg")
    if exe:
        return exe
    try:
        import imageio_ffmpeg

        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        return None


def build_clip(ffmpeg: str, img: Path, out: Path, seconds: float, size: int, zoom_in: bool) -> None:
    """单张图 → 一段带缓慢推拉的视频。"""
    # zoompan: z 从 1.0 缓慢放大到 1.08（或反向），d=帧数
    fps = 30
    frames = int(seconds * fps)
    if zoom_in:
        zexpr = f"1+0.08*on/{frames}"
    else:
        zexpr = f"1.08-0.08*on/{frames}"

    vf = (
        f"scale={size}:{size}:force_original_aspect_ratio=increase,"
        f"crop={size}:{size},"
        f"zoompan=z='{zexpr}':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)'"
        f":d={frames}:s={size}x{size}:fps={fps},"
        f"format=yuv420p"
    )
    cmd = [
        ffmpeg, "-y", "-loglevel", "error",
        "-loop", "1", "-i", str(img),
        "-t", f"{seconds}",
        "-vf", vf,
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
        str(out),
    ]
    subprocess.run(cmd, check=True)


def concat_with_fade(ffmpeg: str, clips: list[Path], out: Path, seconds: float, size: int) -> None:
    """多段拼接，相邻片段加 0.4 秒交叉淡入淡出。"""
    fade = 0.4
    inputs: list[str] = []
    for c in clips:
        inputs += ["-i", str(c)]

    # xfade 链式叠加
    parts = []
    cur = "[0:v]"
    for i in range(1, len(clips)):
        offset = i * (seconds - fade)
        label = f"[v{i}]"
        parts.append(
            f"{cur}[{i}:v]xfade=transition=fade:duration={fade}:offset={offset:.2f}{label}"
        )
        cur = label
    filter_complex = ";".join(parts) if parts else "[0:v]copy"

    cmd = [ffmpeg, "-y", "-loglevel", "error", *inputs,
           "-filter_complex", filter_complex,
           "-map", cur,
           "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
           "-pix_fmt", "yuv420p", str(out)]
    subprocess.run(cmd, check=True)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--images", required=True, help="图片目录")
    ap.add_argument("--out", default="samples/demo.mp4")
    ap.add_argument("--seconds", type=float, default=3.0, help="每张图停留秒数")
    ap.add_argument("--size", type=int, default=1080, help="输出分辨率（正方形）")
    ap.add_argument("--limit", type=int, default=6, help="最多用几张图")
    args = ap.parse_args()

    ffmpeg = find_ffmpeg()
    if not ffmpeg:
        print("❌ 找不到 ffmpeg。装法二选一：")
        print("   pip install imageio-ffmpeg   （推荐，自带二进制）")
        print("   winget install Gyan.FFmpeg")
        sys.exit(1)

    imgs = sorted(
        p for p in Path(args.images).iterdir()
        if p.suffix.lower() in {".png", ".jpg", ".jpeg"}
    )[: args.limit]
    if not imgs:
        print(f"❌ {args.images} 里没有图片")
        sys.exit(1)

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    tmp = out.parent / "_clips"
    shutil.rmtree(tmp, ignore_errors=True)
    tmp.mkdir(parents=True, exist_ok=True)

    print(f"图片 {len(imgs)} 张 → 每张 {args.seconds}s → {out}")
    clips = []
    for i, img in enumerate(imgs):
        clip = tmp / f"clip_{i:02d}.mp4"
        build_clip(ffmpeg, img, clip, args.seconds, args.size, zoom_in=(i % 2 == 0))
        clips.append(clip)
        print(f"  [{i+1}/{len(imgs)}] {img.name} → {clip.name}")

    concat_with_fade(ffmpeg, clips, out, args.seconds, args.size)
    total = len(imgs) * args.seconds - (len(imgs) - 1) * 0.4
    print(f"\n✅ 输出 {out}  时长约 {total:.1f} 秒  {out.stat().st_size/1e6:.1f} MB")


if __name__ == "__main__":
    main()
