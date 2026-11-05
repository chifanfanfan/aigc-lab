# Docker 包一层 ComfyUI（对应 JD 的「Linux 环境部署 / Docker / CUDA」）
#
# 构建：
#   docker build -t comfyui-gpu -f docker/Dockerfile .
# 运行（Windows 需要 Docker Desktop + WSL2 + NVIDIA 驱动）：
#   docker run --gpus all -p 8188:8188 -v %cd%/models:/app/models comfyui-gpu
#
# 说明：本机 Docker 起不来时（我们碰到过 WSL2 装不上），
# 这个 Dockerfile 可以在 GitHub Codespaces 或云服务器上验证。

FROM nvidia/cuda:12.1.1-runtime-ubuntu22.04

ENV DEBIAN_FRONTEND=noninteractive PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y --no-install-recommends \
        python3 python3-pip python3-venv git wget \
    && rm -rf /var/lib/apt/lists/*

RUN git clone https://github.com/comfyanonymous/ComfyUI /app
WORKDIR /app
RUN pip3 install --no-cache-dir torch torchvision --index-url https://download.pytorch.org/whl/cu121 \
    && pip3 install --no-cache-dir -r requirements.txt

# 自定义节点（我们写的批量提示词节点）
COPY custom_nodes/prompt_batch /app/custom_nodes/prompt_batch
COPY prompts.txt /app/prompts.txt

EXPOSE 8188
CMD ["python3", "main.py", "--listen", "0.0.0.0", "--port", "8188"]
