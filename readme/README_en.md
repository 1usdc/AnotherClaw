# AnotherClaw

**Automatically selects the right Agent from user conversation, then invokes skills**; supports multiple Agents and is compatible with open-source skills from [clawhub.io](https://clawhub.io).

[简体中文](README_zh.md) · English · [Español](README_es.md) · [العربية](README_ar.md) · [Français](README_fr.md) · [Русский](README_ru.md) · [Deutsch](README_de.md) · [日本語](README_ja.md) · [Português](README_pt.md) · [Italiano](README_it.md) · [한국어](README_ko.md) · [ไทย](README_th.md)

---

## Requirements

- **Python** 3.10 or higher
- **uv**: for creating virtual environments and installing dependencies (installed automatically on first run of `anotherme start`)
- **OS**: Linux or macOS recommended; on Windows, Docker is recommended

---

## Quick Start

### 0. On macOS or Windows: install Docker and start a Linux container

```bash
# Check that Docker is installed
docker --version
# Start a Docker Ubuntu container
docker run -d -p 8765:8765 --name anotherme ubuntu:latest tail -f /dev/null
# Enter the container
docker exec -it anotherme bash
```

### 1. Install curl

```bash
# Example for Debian/Ubuntu
apt update && apt install -y curl
```

### 2. Quick install

#### Install anotherme

```bash
curl -fsSL https://gist.githubusercontent.com/1usdc/76c0376321abafad0d8da457ac73f006/raw/anotherme.sh | bash
```

#### Reload environment variables

```bash
source ~/.zshrc
```

#### Test commands

```bash
anotherme --version
anotherme --help         # Show usage and all commands
```

#### Start the project

```bash
anotherme start
```

### 3. Common commands

```bash
anotherme --help         # Show usage and all commands
anotherme dev            # Build claw-fe (claw-fe/dist) first, then start backend
anotherme start          # Start (foreground); start --bg for background, logs to anotherme.log
anotherme pack           # Obfuscate and pack into build/; pack --linux for Linux build inside Docker
anotherme push           # Run git init in build/, commit and push to GitHub
anotherme push-openclaw  # One-shot push of project root repo to openclaw (override with OPENCLAW_REPO_URL)
lsof -i :8765            # Check port usage
kill -9 <PID>            # Kill process (replace <PID> with the PID from above)
```

---

## Skills overview

Skills follow a **category → skill directory** layout, aligned with the OpenClaw SKILL spec: each skill is a directory with a required `SKILL.md`, and optional `scripts/`, `references/`, and `assets/`.

### Directory structure

```
skills-name/
├── README.md              # This overview
├── skill-name/            # Skill directory (named after the skill, no category folder needed)
│   ├── SKILL.md           # Required: YAML frontmatter + Markdown body
│   ├── scripts/           # Optional: executable scripts (Python, Bash, etc.)
│   ├── references/        # Optional: docs loaded on demand (API, schema, policies, etc.)
│   └── assets/            # Optional: templates, icons, fonts, etc.; not loaded into context
└── ...
```

Example:

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

### Recommended SKILL.md format

```markdown
---
name: my_skill
description: Short description; state when to use this skill.
keywords: [url, open, link, webpage, visit]
metadata:
    requires:
        env:
            - WEATHER_API_KEY     # Required env vars (e.g. API keys)
        python:
            - requests           # Python dependencies, add as needed
            - pandas
    install:
        - id: uv-weather
          kind: uv                   # Supports uv / pip / shell / apt
          package: weather-cli
          bins:
              - weather
          label: Install weather-cli (via uv)
          check: weather --help
---

# Skill title
Body: use cases, steps, and instructions.
```

---

## Links

- Repository: [github.com/1usdc/AnotherClaw](https://github.com/1usdc/AnotherClaw)
