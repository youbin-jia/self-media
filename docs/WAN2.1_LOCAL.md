# 通义万相 Wan2.1 I2V 本地部署与接入（完整手册）

本仓库已接入 **图生视频**：分镜时间轴在「有参考图」时可调用 Wan2.1 生成短片段后再拼接（见 `backend/app/services/wan_video/`）。

> **权重说明**：推荐官方整目录 **`Wan-AI/Wan2.1-I2V-14B-720P`**（与 `generate.py --ckpt_dir` 一致）。社区 FP8 单文件（如 `wan2.1_i2v_720p_14B_fp8_e4m3fn`）多为 ComfyUI 等场景，**不能**直接当作本脚本里的 `WAN_I2V_CKPT_DIR`，除非自行整理为官方目录结构。

---

## 目录与脚本（自动化）

| 路径 | 说明 |
|------|------|
| `scripts/wan2.1/setup_wan2.1.sh` | 克隆代码、创建 venv、下载权重、生成环境片段 |
| `scripts/wan2.1/start_wan_sidecar.sh` | 启动 HTTP 侧车（GPU 与主 API 可同机或分机） |
| `scripts/wan_i2v_sidecar.py` | 侧车实现：`POST /generate` |
| `third_party/wan2.1/` | **默认安装目录**（已加入 `.gitignore`，不占 Git） |
| `backend/.env.wan.generated` | **脚本生成**，需合并进 `backend/.env` |

快速索引：`scripts/wan2.1/README.md`。

---

## 推荐架构

1. **侧车**（本机 GPU）：跑 `generate.py`，监听 `9810`（可改）。
2. **主 API**（`uvicorn`）：`WAN_I2V_MODE=http`，`WAN_I2V_ENDPOINT` 指向侧车。

这样主项目 **conda/venv 不必装 torch**，避免与 Wan 的 CUDA 版本冲突。

---

## 一键部署（手动在你机器上执行）

在**仓库根目录** `self-media/` 下：

### 步骤 1：安装代码与 Python 环境

```bash
chmod +x scripts/wan2.1/setup_wan2.1.sh scripts/wan2.1/start_wan_sidecar.sh

# 克隆 Wan2.1 + 创建 third_party/wan2.1/venv-wan 并安装依赖（耗时长，需稳定网络）
./scripts/wan2.1/setup_wan2.1.sh all --skip-download
```

`all` 包含：`install-repo` → `venv` → `env-snippet`。

### 步骤 2：下载 I2V 720P 14B 权重

体积大（数十 GB 量级），请预留磁盘与带宽：

```bash
# 可选：export HF_TOKEN=xxx
./scripts/wan2.1/setup_wan2.1.sh download
```

默认仓库：`Wan-AI/Wan2.1-I2V-14B-720P`，目录：`third_party/wan2.1/Wan2.1-I2V-14B-720P`。

### 步骤 3：合并主 API 环境变量

```bash
cat backend/.env.wan.generated >> backend/.env
```

片段内容为 **HTTP 模式**（指向 `http://127.0.0.1:9810`）。若侧车改端口：

```bash
export WAN_SIDECAR_PORT=9810
./scripts/wan2.1/setup_wan2.1.sh env-snippet
```

再重新 `cat` 合并。

### 步骤 4：启动侧车（常驻）

```bash
./scripts/wan2.1/start_wan_sidecar.sh
```

健康检查：

```bash
curl -s http://127.0.0.1:9810/health
```

### 步骤 5：启动主 API

按原流程（如 `./scripts/dev.sh start` 或 `uvicorn app.main:app`）。确保 `backend/.env` 已含 `WAN_I2V_ENABLED=true` 等。

---

## 子命令参考

```text
./scripts/wan2.1/setup_wan2.1.sh install-repo   # 仅克隆
./scripts/wan2.1/setup_wan2.1.sh venv            # 仅 venv + pip
./scripts/wan2.1/setup_wan2.1.sh download        # 仅下载权重
./scripts/wan2.1/setup_wan2.1.sh env-snippet     # 仅重新生成 .env 片段与 wan.runtime.env
./scripts/wan2.1/setup_wan2.1.sh all --skip-download
```

环境变量：

| 变量 | 说明 |
|------|------|
| `HF_TOKEN` | Hugging Face 令牌（可选） |
| `WAN_HF_REPO` | 默认 `Wan-AI/Wan2.1-I2V-14B-720P` |
| `WAN_SIDECAR_PORT` | 侧车端口，默认 `9810` |
| `WAN_AUTO_DOWNLOAD=1` | 与 `all` 联用时自动执行 `download`（慎用） |

---

## 同机 subprocess 模式（可选）

不跑侧车时，在 `backend/.env` 中：

- 设 `WAN_I2V_MODE=subprocess`
- 填写 `WAN_I2V_REPO_DIR`、`WAN_I2V_CKPT_DIR`、`WAN_I2V_PYTHON`（见 `backend/.env.wan.generated` 内注释示例）

注意：主 API 进程会 **子进程调用** `generate.py`，依赖与显存均在同一环境，排错相对复杂。

---

## 显存与参数

官方 README 建议显存紧张时使用，可在 `third_party/wan2.1/wan.runtime.env` 或 `backend/.env` 中设置：

```env
WAN_I2V_EXTRA_ARGS=--offload_model True --t5_cpu
```

超时：

```env
WAN_I2V_TIMEOUT_SEC=7200
```

---

## systemd 常驻侧车（生产可选）

示例：`scripts/wan2.1/systemd/wan-i2v-sidecar.service.example`

```bash
sudo cp scripts/wan2.1/systemd/wan-i2v-sidecar.service.example /etc/systemd/system/wan-i2v-sidecar.service
# 编辑其中 User、WorkingDirectory、ExecStart
sudo systemctl daemon-reload
sudo systemctl enable --now wan-i2v-sidecar
```

---

## 故障排查

| 现象 | 处理 |
|------|------|
| `/health` 503 | 检查 `wan.runtime.env` 路径、`WAN_I2V_CKPT_DIR` 是否已下载且非空 |
| 主 API 不调 Wan | 确认 `WAN_I2V_ENABLED=true`、分镜存在、且该镜有**图片**路径 |
| `generate.py` 报错 | 在 `WAN_I2V_REPO_DIR` 下手动跑官方命令试通（见下） |
| 克隆只有 `.git` 无文件 | 删除 `third_party/wan2.1/Wan2.1` 后重新 `install-repo`（网络中断会导致半成品） |

手动试跑官方命令（与侧车一致逻辑）：

```bash
source third_party/wan2.1/venv-wan/bin/activate
cd third_party/wan2.1/Wan2.1
python generate.py --task i2v-14B --size 1280*720 \
  --ckpt_dir ../Wan2.1-I2V-14B-720P \
  --image examples/i2v_input.JPG \
  --prompt "测试镜头运动与光影" \
  --save_file /tmp/wan_smoke.mp4
```

---

## 相关链接

- [Wan-Video/Wan2.1](https://github.com/Wan-Video/Wan2.1)
- [Wan2.1-I2V-14B-720P（HF）](https://huggingface.co/Wan-AI/Wan2.1-I2V-14B-720P)
