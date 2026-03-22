# 镜像与代理（GitHub / Hugging Face）

在 **github.com 或 huggingface.co 访问不稳定** 时，可用下列方式（多为**第三方服务**，可用性会变化，请自行判断是否合规、是否仍可用）。

---

## Hugging Face（下载模型、CLI）

本仓库脚本已支持：

```bash
export HF_ENDPOINT=https://hf-mirror.com
```

然后再执行 `hf download`、`./scripts/ltx2/download_ltx2_gguf.sh` 等。

也可使用 **HTTP(S) 代理**（端口按你本机代理修改）：

```bash
export HTTPS_PROXY=http://127.0.0.1:7890
export HTTP_PROXY=http://127.0.0.1:7890
```

---

## GitHub（git clone）

### 方式 A：本仓库 LTX Comfy 安装脚本内置别名

执行 **`./scripts/ltx2/setup_comfyui_ltx2.sh`** 前任选其一：

```bash
# 预设镜像（脚本内会改写克隆 URL）
export LTX2_GITHUB_MIRROR=ghproxy        # https://ghproxy.net/ + 原 GitHub URL
export LTX2_GITHUB_MIRROR=mirror        # mirror.ghproxy.com
export LTX2_GITHUB_MIRROR=kkgithub        # 将 github.com 换为 kkgithub.com
export LTX2_GITHUB_MIRROR=gitclone        # gitclone.com/github.com/... 形式
```

**优先级更高**的自定义前缀（任意你信任的代理前缀）：

```bash
export LTX2_GIT_PREFIX=https://ghproxy.net
./scripts/ltx2/setup_comfyui_ltx2.sh
```

规则：`最终克隆地址 = ${LTX2_GIT_PREFIX} + / + https://github.com/...`（前缀不要多余一层路径，一般与 ghproxy 类站点文档一致）。

### 方式 B：给 Git 配置 HTTP 代理

本机已开 Clash / V2Ray 等 **HTTP 代理** 时：

```bash
git config --global http.https://github.com.proxy http://127.0.0.1:7890
git config --global https.https://github.com.proxy http://127.0.0.1:7890
```

取消代理：

```bash
git config --global --unset http.https://github.com.proxy
git config --global --unset https.https://github.com.proxy
```

### 方式 C：浏览器下载 ZIP / 手动拷贝

1. 在能打开 GitHub 的网络下，打开仓库页 **Code → Download ZIP**。  
2. 解压到本仓库约定目录，**文件夹名字必须与下表一致**（GitHub ZIP 常带 `-main` 后缀，需**去掉并重命名**）。

---

#### LTX-2 + ComfyUI 一键环境需要哪几个仓库？

在浏览器分别打开下列页面，点 **Code → Download ZIP**，共 **4 个 ZIP**：

| # | GitHub 仓库（在浏览器打开） | 解压后常见顶层目录名 | **必须改成/放到**（相对本仓库根目录 `self-media/`） |
|---|----------------------------|----------------------|------------------------------------------------------|
| 1 | [comfyanonymous/ComfyUI](https://github.com/comfyanonymous/ComfyUI) | `ComfyUI-main` | → **`third_party/ltx2/ComfyUI/`**（根目录下要有 `main.py`、`requirements.txt`） |
| 2 | [ltdrdata/ComfyUI-Manager](https://github.com/ltdrdata/ComfyUI-Manager) | `ComfyUI-Manager-main` | → **`third_party/ltx2/ComfyUI/custom_nodes/ComfyUI-Manager/`** |
| 3 | [city96/ComfyUI-GGUF](https://github.com/city96/ComfyUI-GGUF) | `ComfyUI-GGUF-main` | → **`third_party/ltx2/ComfyUI/custom_nodes/ComfyUI-GGUF/`** |
| 4 | [Lightricks/ComfyUI-LTXVideo](https://github.com/Lightricks/ComfyUI-LTXVideo) | `ComfyUI-LTXVideo-main`（或类似） | → **`third_party/ltx2/ComfyUI/custom_nodes/ComfyUI-LTXVideo/`** |

**操作顺序建议：**

1. 在 **`third_party/ltx2/`** 下准备目录（没有就新建）：最终会需要 **`third_party/ltx2/ComfyUI/custom_nodes/`**。  
2. 解压 **ComfyUI** 的 ZIP：若得到文件夹 **`ComfyUI-main`**，请**改名为 `ComfyUI`**，并移动到 **`third_party/ltx2/ComfyUI`**。  
   正确标志：存在文件 **`third_party/ltx2/ComfyUI/main.py`**（中间不要多一层 `ComfyUI/ComfyUI/`）。  
3. 另外三个 ZIP 各自解压，**去掉 `-main` 后缀**，分别放进 **`third_party/ltx2/ComfyUI/custom_nodes/`** 下，使存在：  
   - `.../custom_nodes/ComfyUI-Manager/`  
   - `.../custom_nodes/ComfyUI-GGUF/`  
   - `.../custom_nodes/ComfyUI-LTXVideo/`  

**GGUF 模型**不是 GitHub 下的，仍用脚本从 Hugging Face 下载（或你已有文件），放在：

- **`third_party/ltx2/models/ltx-2-19b-dev-Q5_K_M.gguf`**（文件名可与 `LTX2_GGUF_FILE` 一致）

放好后，**不再 git 克隆**，只装 Python 依赖并链接模型：

```bash
cd ~/Code/self-media
export LTX2_SKIP_GIT_CLONE=1
./scripts/ltx2/setup_comfyui_ltx2.sh
```

脚本会创建 **`third_party/ltx2/venv-comfyui`**、`pip install` 各 `requirements.txt`，并把 GGUF **软链**到 `ComfyUI/models/unet/`。

无法使用 `git clone` 时，用浏览器下 ZIP 按上表摆放即可。

### 方式 D：Gitee / 其他代码镜像

若有人同步了**同名镜像仓库**，可 `git clone` 镜像地址，再 `cd` 到脚本期望路径。版本可能滞后，需自行核对提交。

---

## 与本文档相关的脚本

| 脚本 | 环境变量 |
|------|-----------|
| `scripts/ltx2/download_ltx2_gguf.sh` | `HF_ENDPOINT`、`HTTPS_PROXY` |
| `scripts/ltx2/setup_comfyui_ltx2.sh` | `LTX2_GITHUB_MIRROR`、`LTX2_GIT_PREFIX`、`LTX2_SKIP_GIT_CLONE=1`（手动 ZIP 后）、系统 `git` 代理 |

更多说明见 **`scripts/ltx2/README.md`**、**`docs/LTX2_LOCAL.md`**。
