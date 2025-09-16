## 👉🏻 CognitiveKernel-Launchpad 👈🏻

<center><h3>深度研究智能体与基础模型的开放推理运行时框架</h3></center>

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
  <a href='https://www.modelscope.cn/studios/mirror013/CognitiveKernel-Launchpad/summary'>
    <img src='https://img.shields.io/badge/ModelScope-Demo-purple?logo=modelscope'/>
  </a>
</div>


> 🎓 仅用于学术研究与教学使用 — 禁止商用
> 📄 [论文（arXiv:2508.00414）](https://arxiv.org/abs/2508.00414) | 🇬🇧 [English](readme.md) | 📜 [LICENSE](LICENSE.txt)



---

### 摘要

本研究用分支源自腾讯 CognitiveKernel-Pro，专注推理时使用：移除训练/SFT 与重型测试流水线，提供简洁的多步推理代理（Web/文件模块化）与轻量级 Gradio 界面，便于部署与在线演示。

---

## 🚀 快速开始
想要快速上手：直接在线体验 — ModelScope（国内）https://www.modelscope.cn/studios/mirror013/CognitiveKernel-Launchpad/summary | Hugging Face（国外）https://huggingface.co/spaces/Chars/CognitiveKernel-Launchpad

### 1. 安装

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

#### 🚀 推荐配置

基于当前设置，以下是获得最佳性能的推荐配置：

```toml
# 核心智能体配置
[ck.model]
call_target = "https://api-inference.modelscope.cn/v1/chat/completions"
api_key = "your-modelscope-api-key-here"  # 请替换为您的实际密钥
model = "Qwen/Qwen3-235B-A22B-Instruct-2507"

[ck.model.extract_body]
temperature = 0.6
max_tokens = 8192

# Web智能体配置（用于网页浏览任务）
[web]
max_steps = 20
use_multimodal = "auto"  # 需要时自动使用多模态

[web.model]
call_target = "https://api-inference.modelscope.cn/v1/chat/completions"
api_key = "your-modelscope-api-key-here"  # 请替换为您的实际密钥
model = "moonshotai/Kimi-K2-Instruct"
request_timeout = 600
max_retry_times = 5
max_token_num = 8192

[web.model.extract_body]
temperature = 0.0
top_p = 0.95
max_tokens = 8192

# 多模态Web智能体（用于视觉任务）
[web.model_multimodal]
call_target = "https://api-inference.modelscope.cn/v1/chat/completions"
api_key = "your-modelscope-api-key-here"  # 请替换为您的实际密钥
model = "Qwen/Qwen2.5-VL-72B-Instruct"
request_timeout = 600
max_retry_times = 5
max_token_num = 8192

[web.model_multimodal.extract_body]
temperature = 0.0
top_p = 0.95
max_tokens = 8192

# 搜索配置
[search]
backend = "duckduckgo"  # 推荐：可靠且无需API密钥
```

#### 🔑 API密钥设置

1. **获取ModelScope API密钥**：访问 [ModelScope](https://www.modelscope.cn/) 获取您的API密钥
2. **替换占位符**：将所有 `your-modelscope-api-key-here` 替换为您的实际API密钥
3. **替代方案**：使用环境变量：
   ```bash
   export MODELSCOPE_API_KEY="your-actual-key"
   ```

#### 📋 模型选择理由

- **主智能体**：`Qwen3-235B-A22B-Instruct-2507` - 最新高性能推理模型
- **Web智能体**：`Kimi-K2-Instruct` - 针对网页交互任务优化
- **多模态**：`Qwen2.5-VL-72B-Instruct` - 先进的视觉-语言能力

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
