# 自媒体视频自动化平台 - Dockerfile (Miniconda)
FROM continuumio/miniconda3:latest

# 设置环境变量
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app/backend

# 设置工作目录
WORKDIR /app

# 复制 conda 环境配置文件
COPY environment.yml ./environment.yml

# 创建 conda 环境
RUN conda env create -f environment.yml && \
    conda clean -afy

# 激活 conda 环境
SHELL ["conda", "run", "-n", "self-media", "/bin/bash", "-c"]

# 复制应用代码
COPY backend/ ./backend/
COPY plugins/ ./plugins/

# 创建数据目录
RUN mkdir -p /app/data

# 暴露端口
EXPOSE 8000

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# 启动命令
WORKDIR /app/backend
CMD ["conda", "run", "-n", "self-media", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
