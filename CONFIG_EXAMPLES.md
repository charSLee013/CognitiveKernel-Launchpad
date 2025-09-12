# Cognitive Kernel-Pro 配置示例

本文档提供完整的TOML配置文件示例，帮助您根据不同的使用场景进行配置。

## 📋 配置选项总览

### 快速开始选项

| 方法 | 适用场景 | 配置复杂度 | 推荐指数 |
|------|----------|------------|----------|
| **环境变量** | 新用户快速开始 | ⭐ | ⭐⭐⭐⭐⭐ |
| **最小配置** | 标准使用 | ⭐⭐ | ⭐⭐⭐⭐ |
| **全面配置** | 高级定制 | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ |

## 🚀 环境变量方式 (推荐新用户)

### 无需配置文件，直接使用环境变量：

```bash
# 设置环境变量
export OPENAI_API_BASE="https://api.openai.com/v1/chat/completions"
export OPENAI_API_KEY="your-api-key-here"
export OPENAI_API_MODEL="gpt-4o-mini"

# 运行
python -m ck_pro --input "What is AI?"
```

### 优势
- ✅ **零配置**：无需创建任何文件
- ✅ **快速启动**：5秒内开始使用
- ✅ **容器友好**：完美支持Docker/K8s
- ✅ **安全管理**：敏感信息环境变量管理

## 📁 最小配置文件

适用于大多数标准使用场景，只需要配置核心组件。

```toml
# config.minimal.toml
[ck.model]
call_target = "https://api.openai.com/v1/chat/completions"
api_key = "your-api-key-here"
model = "gpt-4o-mini"

[ck.model.extract_body]
temperature = 0.6
max_tokens = 4000

[ck]
max_steps = 16
max_time_limit = 600

[search]
backend = "duckduckgo"
```

### 使用方法
```bash
cp config.minimal.toml config.toml
# 编辑config.toml中的API密钥
python -m ck_pro --input "What is AI?"
```

## ⚙️ 全面配置文件

包含所有可用配置选项，适用于需要完全控制系统的场景。

```toml
# config.comprehensive.toml - 完整示例见同目录文件
[ck]
name = "ck_agent"
description = "Cognitive Kernel, an initial autopilot system."
max_steps = 16
max_time_limit = 6000
recent_steps = 5
obs_max_token = 8192
exec_timeout_with_call = 1000
exec_timeout_wo_call = 200
end_template = "more"

[ck.model]
call_target = "https://api.openai.com/v1/chat/completions"
api_key = "your-openai-api-key"
model = "gpt-4o-mini"
request_timeout = 600
max_retry_times = 5
max_token_num = 20000

# ... 更多配置选项见 config.comprehensive.toml
```

## 🔧 配置说明

### 核心配置 [ck]

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `name` | "ck_agent" | 代理名称 |
| `max_steps` | 16 | 最大推理步骤数 |
| `max_time_limit` | 6000 | 最大执行时间(秒) |
| `end_template` | "more" | 结束模板详细程度 |

### 模型配置 [ck.model]

| 参数 | 类型 | 说明 |
|------|------|------|
| `call_target` | string | API端点URL |
| `api_key` | string | API密钥 |
| `model` | string | 模型名称 |
| `request_timeout` | int | 请求超时时间 |
| `max_retry_times` | int | 最大重试次数 |

### Web代理配置 [web]

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `max_steps` | 20 | Web任务最大步骤数 |
| `use_multimodal` | "auto" | 是否使用多模态(off/yes/auto) |

### 文件代理配置 [file]

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `max_steps` | 16 | 文件处理最大步骤数 |
| `max_file_read_tokens` | 3000 | 文件读取最大token数 |
| `max_file_screenshots` | 2 | 文件截图最大数量 |

### 日志配置 [logging]

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `console_level` | "INFO" | 控制台日志级别 |
| `log_dir` | "logs" | 日志目录 |
| `session_logs` | true | 是否启用会话日志 |

### 搜索配置 [search]

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `backend` | "duckduckgo" | 搜索引擎(duckduckgo/google) |

## 🎯 优先级顺序

配置值的优先级从高到低：

1. **TOML配置文件** - 最高优先级
2. **继承机制** - 子组件继承父组件设置
3. **环境变量** - 中等优先级
4. **硬编码默认值** - 最低优先级

### 继承示例

```toml
[ck.model]
call_target = "https://api.openai.com/v1/chat/completions"
api_key = "shared-key"

[web.model]
# 自动继承 call_target 和 api_key
model = "gpt-4-vision"  # 只覆盖模型名称

[file.model]
call_target = "https://different-api.com"  # 覆盖继承的设置
api_key = "different-key"  # 覆盖继承的设置
model = "claude-3-sonnet"  # 指定不同模型
```

## 🚀 快速开始指南

### 场景1: 新用户快速开始
```bash
# 方式1: 环境变量 (推荐)
export OPENAI_API_KEY="your-key"
export OPENAI_API_MODEL="gpt-4o-mini"
python -m ck_pro --input "Hello world"

# 方式2: 最小配置
cp config.minimal.toml config.toml
# 编辑API密钥
python -m ck_pro --config config.toml --input "Hello world"
```

### 场景2: 多模型配置
```toml
[ck.model]
call_target = "https://api.openai.com/v1/chat/completions"
api_key = "openai-key"
model = "gpt-4o-mini"

[web.model]
call_target = "https://api.siliconflow.cn/v1/chat/completions"
api_key = "siliconflow-key"
model = "Kimi-K2-Instruct"

[file.model]
call_target = "https://api-inference.modelscope.cn/v1/chat/completions"
api_key = "modelscope-key"
model = "Qwen/Qwen3-235B-A22B-Instruct-2507"
```

### 场景3: 生产环境部署
```bash
# Docker环境变量注入
docker run -e OPENAI_API_KEY="prod-key" \
           -e OPENAI_API_MODEL="gpt-4o" \
           cognitivekernel-pro

# Kubernetes ConfigMap
apiVersion: v1
kind: ConfigMap
metadata:
  name: ck-config
data:
  OPENAI_API_BASE: "https://api.openai.com/v1/chat/completions"
  OPENAI_API_MODEL: "gpt-4o"
```

## ❓ 常见问题

### Q: 配置文件不存在会怎样？
A: 系统会自动使用环境变量或硬编码默认值，不会出现错误。

### Q: 如何验证配置是否正确？
A: 运行简单查询测试：`python -m ck_pro --input "test"`

### Q: 支持哪些模型？
A: 支持所有兼容OpenAI API格式的模型，包括GPT、Claude、Qwen等。

### Q: 如何切换不同的模型配置？
A: 修改`config.toml`中的`[ck.model]`、`[web.model]`、`[file.model]`部分。

## 📚 相关文档

- [readme.md](readme.md) - 项目主要文档
- [docs/ARCH.md](docs/ARCH.md) - 架构设计文档
- [docs/PLAYWRIGHT_BUILTIN.md](docs/PLAYWRIGHT_BUILTIN.md) - Web自动化文档