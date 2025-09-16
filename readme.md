## 👉🏻 CognitiveKernel-Launchpad 👈🏻

<center><h3>Open Framework for Deep Research Agents & Agent Foundation Models</h3></center>

<div align="center">
  <a href='https://arxiv.org/abs/2508.00414'>
    <img src='https://img.shields.io/badge/ArXiv-2508.00414-red?logo=arxiv'/>
  </a>
  <br/>
  <a href='https://github.com/charSLee013/CognitiveKernel-Launchpad'>
    <img src='https://img.shields.io/badge/GitHub-Code-orange?logo=github'/>
  </a>
  <a href='https://huggingface.co/spaces/Chars/CognitiveKernel-Launchpad'>
    <img src='https://img.shields.io/badge/HuggingFace-Demo-blue?logo=huggingface'/>
  </a>
  <a href='https://www.modelscope.cn/studios/mirror013/CognitiveKernel-Launchpad'>
    <img src='https://img.shields.io/badge/ModelScope-Demo-purple?logo=modelscope'/>
  </a>
</div>

> 🎓 **Academic Research & Educational Use Only** — No Commercial Use
> 📄 [Paper (arXiv:2508.00414)](https://arxiv.org/abs/2508.00414) | 🇨🇳 [中文文档](README_zh.md) | 📜 [LICENSE](LICENSE.txt)

---

### Abstract

A research-only fork of Tencent's CognitiveKernel-Pro focused on inference-time usage. It simplifies the runtime by removing training/SFT and heavy test pipelines, providing a clean multi-step reasoning agent with modular Web/File tools and a lightweight Gradio UI for easy deployment and online demos.

---

## 🚀 Quick Start
Quickest path: use the online demo — ModelScope (CN) https://www.modelscope.cn/studios/mirror013/CognitiveKernel-Launchpad/summary | Hugging Face (Global) https://huggingface.co/spaces/Chars/CognitiveKernel-Launchpad

### 1. Install

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

#### 🚀 Recommended Configuration

Based on the current setup, here's the recommended configuration for optimal performance:

```toml
# Core Agent Configuration
[ck.model]
call_target = "https://api-inference.modelscope.cn/v1/chat/completions"
api_key = "your-modelscope-api-key-here"  # Replace with your actual key
model = "Qwen/Qwen3-235B-A22B-Instruct-2507"

[ck.model.extract_body]
temperature = 0.6
max_tokens = 8192

# Web Agent Configuration (for web browsing tasks)
[web]
max_steps = 20
use_multimodal = "auto"  # Automatically use multimodal when needed

[web.model]
call_target = "https://api-inference.modelscope.cn/v1/chat/completions"
api_key = "your-modelscope-api-key-here"  # Replace with your actual key
model = "moonshotai/Kimi-K2-Instruct"
request_timeout = 600
max_retry_times = 5
max_token_num = 8192

[web.model.extract_body]
temperature = 0.0
top_p = 0.95
max_tokens = 8192

# Multimodal Web Agent (for visual tasks)
[web.model_multimodal]
call_target = "https://api-inference.modelscope.cn/v1/chat/completions"
api_key = "your-modelscope-api-key-here"  # Replace with your actual key
model = "Qwen/Qwen2.5-VL-72B-Instruct"
request_timeout = 600
max_retry_times = 5
max_token_num = 8192

[web.model_multimodal.extract_body]
temperature = 0.0
top_p = 0.95
max_tokens = 8192

# Search Configuration
[search]
backend = "duckduckgo"  # Recommended: reliable and no API key required
```

#### 🔑 API Key Setup

1. **Get ModelScope API Key**: Visit [ModelScope](https://www.modelscope.cn/) to obtain your API key
2. **Replace placeholders**: Update all `your-modelscope-api-key-here` with your actual API key
3. **Alternative**: Use environment variables:
   ```bash
   export MODELSCOPE_API_KEY="your-actual-key"
   ```

#### 📋 Model Selection Rationale

- **Main Agent**: `Qwen3-235B-A22B-Instruct-2507` - Latest high-performance reasoning model
- **Web Agent**: `Kimi-K2-Instruct` - Optimized for web interaction tasks
- **Multimodal**: `Qwen2.5-VL-72B-Instruct` - Advanced vision-language capabilities

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
