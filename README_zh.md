# 🧠 CognitiveKernel-Launchpad — 深度研究智能体与基础模型的开放推理运行时框架

> 🎓 仅用于学术研究与教学使用 — 禁止商用
> 📄 [论文（arXiv:2508.00414）](https://arxiv.org/abs/2508.00414) | 🇬🇧 [English](readme.md) | 📜 [LICENSE](LICENSE.txt)

[![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-blue)](https://www.python.org/)
[![arXiv](https://img.shields.io/badge/arXiv-2508.00414-b31b1b.svg)](https://arxiv.org/abs/2508.00414)

---

## 🌟 为什么选择 CognitiveKernel-Launchpad？

本研究用途的分支派生自腾讯的 CognitiveKernel-Pro，专为推理时使用优化：剔除了复杂的训练/SFT 与繁重测试流水线，聚焦于简洁稳定的推理运行时，便于分布式部署与推理落地；同时新增轻量级 Gradio 网页界面，便于交互使用。

---

## 🚀 快速开始

### 1. 安装（无需 GPU）

```bash
git clone https://github.com/charSLee013/CognitiveKernel-Launchpad.git
cd CognitiveKernel-Launchpad
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 2. 设置环境变量（最小化配置）

```bash
export OPENAI_API_KEY="sk-..."
export OPENAI_API_BASE="https://api.openai.com/v1"
export OPENAI_API_MODEL="gpt-4o-mini"
```

### 3. 运行单个问题

```bash
python -m ck_pro "What is the capital of France?"
```

✅ 就这么简单！你已经在运行一个深度研究智能体。

---

## 🛠️ 核心特性

### 🖥️ 命令行接口

```bash
python -m ck_pro \
  --config config.toml \
  --input questions.txt \
  --output answers.txt \
  --interactive \
  --verbose
```

| 参数 | 说明 |
|------|------|
| `-c, --config` | TOML 配置路径（可选） |
| `-i, --input` | 批量输入文件（每行一个问题） |
| `-o, --output` | 将答案输出到文件 |
| `--interactive` | 交互式问答模式 |
| `-v, --verbose` | 显示推理步骤与耗时 |

---

### ⚙️ 配置（config.toml）

> `TOML > 环境变量 > 默认值`

使用本仓库提供的两份示例：
- 最小配置：[config.minimal.toml](config.minimal.toml) —— 详细说明见 [CONFIG_EXAMPLES.md](CONFIG_EXAMPLES.md)
- 全面配置：[config.comprehensive.toml](config.comprehensive.toml) —— 完整字段与继承示例见 [CONFIG_EXAMPLES.md](CONFIG_EXAMPLES.md)

最小配置（即可运行）：
```toml
[ck.model]
call_target = "https://api.openai.com/v1/chat/completions"
api_key = "your-api-key"
model = "gpt-4o-mini"
```

完整配置与高级选项请参见 [CONFIG_EXAMPLES.md](CONFIG_EXAMPLES.md)。

---

### 📊 GAIA 基准评测

评测你的智能体在 GAIA 基准上的表现：

```bash
python -m gaia.cli.simple_validate \
  --data gaia_val.jsonl \
  --level all \
  --count 10 \
  --output results.jsonl
```

→ 输出详细的性能汇总与逐任务结果。

---

### 🌐 Gradio Web 界面

启动一个更友好的网页界面：

```bash
python -m ck_pro.gradio_app --host 0.0.0.0 --port 7860
```

→ 在浏览器打开 `http://localhost:7860`。

提示：推荐预先安装 Playwright 浏览器（或在遇到相关错误时再安装）：`python -m playwright install`（Linux 可能还需执行 `python -m playwright install-deps`）。


---

### 📂 日志

- 控制台：默认 `INFO` 级别
- 会话日志：`logs/ck_session_*.log`
- 可在 TOML 的 `[logging]` 部分进行配置

---

## 🧩 架构要点

- 模块化设计：Web、文件、代码、推理模块
- 回退机制：HTTP API → Playwright 浏览器自动化
- 反思与投票：面向测试时优化的策略以提升准确率
- 可扩展：易于接入新模型、工具或数据集

---

## 📜 许可证与致谢

这是 **腾讯 CognitiveKernel-Pro** 的研究用分支。
🔗 原仓库：https://github.com/Tencent/CognitiveKernel-Pro

> ⚠️ 严格用于学术研究与教学用途，禁止商用。
> 详见 `LICENSE.txt`。
