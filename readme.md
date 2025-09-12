# 🧠 CognitiveKernel-Launchpad — Open Framework for Deep Research Agents & Agent Foundation Models

> 🎓 **Academic Research & Educational Use Only** — No Commercial Use
> 📄 [Paper (arXiv:2508.00414)](https://arxiv.org/abs/2508.00414) | 🇨🇳 [中文文档](README_zh.md) | 📜 [LICENSE](LICENSE.txt)

[![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-blue)](https://www.python.org/)
[![arXiv](https://img.shields.io/badge/arXiv-2508.00414-b31b1b.svg)](https://arxiv.org/abs/2508.00414)

---

## 🌟 Why CognitiveKernel-Launchpad?

This research-only fork is derived from Tencent's original CognitiveKernel-Pro and is purpose-built for inference-time usage. It removes complex training/SFT and heavy testing pipelines, focusing on a clean reasoning runtime that is easy to deploy for distributed inference. In addition, it includes a lightweight Gradio web UI for convenient usage.

---

## 🚀 Quick Start

### 1. Install (No GPU Required)

```bash
git clone https://github.com/charSLee013/CognitiveKernel-Launchpad.git
cd CognitiveKernel-Launchpad
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Set Environment (Minimal Setup)

```bash
export OPENAI_API_KEY="sk-..."
export OPENAI_API_BASE="https://api.openai.com/v1"
export OPENAI_API_MODEL="gpt-4o-mini"
```

### 3. Run a Single Question

```bash
python -m ck_pro "What is the capital of France?"
```

✅ That’s it! You’re running a deep research agent.

---

## 🛠️ Core Features

### 🖥️ CLI Interface
```bash
python -m ck_pro \
  --config config.toml \
  --input questions.txt \
  --output answers.txt \
  --interactive \
  --verbose
```

| Flag          | Description                          |
|---------------|--------------------------------------|
| `-c, --config`| TOML config path (optional)          |
| `-i, --input` | Batch input file (one Q per line)    |
| `-o, --output`| Output answers to file               |
| `--interactive`| Start interactive Q&A session       |
| `-v, --verbose`| Show reasoning steps & timing       |

---

### ⚙️ Configuration (config.toml)

> `TOML > Env Vars > Defaults`

Use the examples in this repo:
- Minimal config: [config.minimal.toml](config.minimal.toml) — details in [CONFIG_EXAMPLES.md](CONFIG_EXAMPLES.md)
- Comprehensive config: [config.comprehensive.toml](config.comprehensive.toml) — full explanation in [CONFIG_EXAMPLES.md](CONFIG_EXAMPLES.md)

Minimal (just works):
```toml
[ck.model]
call_target = "https://api.openai.com/v1/chat/completions"
api_key = "your-api-key"
model = "gpt-4o-mini"
```

For all other options, see [CONFIG_EXAMPLES.md](CONFIG_EXAMPLES.md).

---

### 📊 GAIA Benchmark Evaluation

Evaluate your agent on the GAIA benchmark:

```bash
python -m gaia.cli.simple_validate \
  --data gaia_val.jsonl \
  --level all \
  --count 10 \
  --output results.jsonl
```

→ Outputs detailed performance summary & per-task results.

---

### 🌐 Gradio Web UI

Launch a user-friendly web interface:

```bash
python -m ck_pro.gradio_app --host 0.0.0.0 --port 7860
```

→ Open `http://localhost:7860` in your browser.


Note: It is recommended to install Playwright browsers (or install them if you encounter related errors). On Linux you may also need to run playwright install-deps.

Note: It is recommended to install Playwright browsers (or install them if you encounter related errors): `python -m playwright install` (Linux may also require `python -m playwright install-deps`).

---

### 📂 Logging

- Console: `INFO` level by default
- Session logs: `logs/ck_session_*.log`
- Configurable via `[logging]` section in TOML

---

## 🧩 Architecture Highlights

- **Modular Design**: Web, File, Code, Reasoning modules
- **Fallback Mechanism**: HTTP API → Playwright browser automation
- **Reflection & Voting**: Novel test-time strategies for improved accuracy
- **Extensible**: Easy to plug in new models, tools, or datasets

---

## 📜 License & Attribution

This is a research-only fork of **Tencent’s CognitiveKernel-Pro**.
🔗 Original: https://github.com/Tencent/CognitiveKernel-Pro

> ⚠️ **Strictly for academic research and educational purposes. Commercial use is prohibited.**
> See `LICENSE.txt` for full terms.
