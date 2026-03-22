# Wan2.1（通义万相）本地部署脚本

完整说明见仓库根目录 **[`docs/WAN2.1_LOCAL.md`](../../docs/WAN2.1_LOCAL.md)**。

## 一键顺序（推荐）

在仓库根目录执行：

```bash
# 1) 克隆官方仓库 + 创建独立 venv + 安装依赖（不含权重）
./scripts/wan2.1/setup_wan2.1.sh all --skip-download

# 2) 下载 I2V 720P 14B 权重（体积大，需较长时间与磁盘空间）
./scripts/wan2.1/setup_wan2.1.sh download

# 3) 生成 backend/.env 合并用片段并打印说明
./scripts/wan2.1/setup_wan2.1.sh env-snippet
```

将 `backend/.env.wan.generated` 中的内容**追加**到 `backend/.env`，然后启动侧车：

```bash
./scripts/wan2.1/start_wan_sidecar.sh
```

主 API 使用 **HTTP 模式** 连接侧车（见生成片段中的 `WAN_I2V_MODE=http`）。

## 单步子命令

| 命令 | 说明 |
|------|------|
| `install-repo` | 浅克隆 `Wan-Video/Wan2.1` → `third_party/wan2.1/Wan2.1` |
| `venv` | 创建 `third_party/wan2.1/venv-wan` 并 `pip install -r requirements.txt` + fastapi/uvicorn |
| `download` | `huggingface-cli download Wan-AI/Wan2.1-I2V-14B-720P` |
| `env-snippet` | 写入 `backend/.env.wan.generated`（绝对路径） |
| `all` | 依次 `install-repo` + `venv`（可加 `--skip-download`） |

**systemd 常驻示例**：`scripts/wan2.1/systemd/wan-i2v-sidecar.service.example`

环境变量（可选）：

- `HF_TOKEN`：Hugging Face 令牌（部分模型/限速时需要）
- `WAN_HF_REPO`：默认 `Wan-AI/Wan2.1-I2V-14B-720P`
