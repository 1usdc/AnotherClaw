# AnotherClaw

**根据用户对话自动选择合适的 Agent 执行，再调用技能**；支持多 Agent，兼容 [clawhub.io](https://clawhub.io) 的开源技能。

简体中文 · [English](README_en.md) · [Español](README_es.md) · [العربية](README_ar.md) · [Français](README_fr.md) · [Русский](README_ru.md) · [Deutsch](README_de.md) · [日本語](README_ja.md) · [Português](README_pt.md) · [Italiano](README_it.md) · [한국어](README_ko.md) · [ไทย](README_th.md)

---

## 环境要求

- **Python** 3.10 及以上
- **uv**：用于创建虚拟环境与安装依赖（首次执行 `anotherme start` 时会自动安装）
- **系统**：推荐 Linux, macOS；Windows 建议使用 docker

---

## 快速开始
### 0. 如果是 macOS 或 Windows 需要先安装docker，然后用docker启动一个linux容器
```bash
# 判断 docker 是否安装成功
docker --version
# 启动docker ubuntu容器
docker run -d -p 8765:8765 --name anotherme ubuntu:latest tail -f /dev/null
# 进入容器
docker exec -it anotherme bash
```


### 1. 安装curl命令

```bash
# 以 Debian/Ubuntu 为例
apt update && apt install -y curl
```

### 2. 快速安装

## 安装 anotherme
```bash
curl -fsSL https://gist.anotherme.co | bash
```

## 更新环境变量
```bash
source ~/.zshrc
```
## 测试命令
```bash
anotherme --version
anotherme --help         # 查看用法与全部命令
```
## 启动项目
```bash
anotherme start
```

### 3. 常用命令

```bash
anotherme --help         # 查看用法与全部命令
anotherme dev            # 先打包前端 (claw-fe/dist)，再启动后端
anotherme start          # 启动（前台）；start --bg 后台启动，日志写入 anotherme.log
anotherme pack           # 混淆并打包到 build/；pack --linux 在 Docker 内打 Linux 版
anotherme push           # 对 build/ 执行 git init、提交并推送到 GitHub
anotherme push-openclaw  # 一键推送项目根仓库到 openclaw（可用 OPENCLAW_REPO_URL 覆盖）
lsof -i :8765            # 查看端口占用
kill -9 <PID>            # 结束进程（将 <PID> 替换为上面输出的进程号）
```

---

## 技能库说明

技能采用 **大类 → 技能目录** 结构，与 OpenClaw SKILL 规范一致：每个技能是一个目录，内含必选的 `SKILL.md`，以及可选的 `scripts/`、`references/`、`assets/`。

### 目录结构

```
skills-name/
├── README.md              # 本说明
├── skill-name/             # 技能目录（以技能名命名，无需大类）
│   ├── SKILL.md            # 必选：YAML frontmatter + Markdown 正文
│   ├── scripts/            # 可选：可执行脚本（Python/Bash 等）
│   ├── references/        # 可选：供按需加载的文档（API、schema、策略等）
│   └── assets/            # 可选：模板、图标、字体等，不加载进上下文
└── ...
```

示例：

```
skills/
├── example/
│   └── SKILL.md
├── example_template/
│   ├── SKILL.md
│   └── scripts/
│       └── main.py
└── api-doc/
    ├── SKILL.md
    └── references/
        └── api-spec.md
```

### SKILL.md 推荐格式

```markdown
---
name: my_skill
description: 简短描述，写清何时使用。
keywords: [url, 打开, 链接, 网页, 访问]
metadata:
    requires:
        env:
            - WEATHER_API_KEY     # 需要的环境变量（如 API key 等）
        python:
            - requests           # 依赖的 Python 库，可按需增加
            - pandas
    install:
        - id: uv-weather
          kind: uv                   # 支持 uv / pip / shell / apt
          package: weather-cli
          bins:
              - weather
          label: 安装 weather-cli (通过 uv)
          check: weather --help
---

# 技能标题
正文：使用场景、步骤与说明等。
```

---

## 相关链接

- 仓库：[github.com/1usdc/AnotherClaw](https://github.com/1usdc/AnotherClaw)
