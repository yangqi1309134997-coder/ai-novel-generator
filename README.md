# AI 小说工坊 4.5

> 基于大语言模型的智能小说生成平台，支持本地单机使用和商业多租户部署。

**版权所有 &copy; 2026 新疆幻城网安科技有限责任公司（幻城科技）**

---

## 产品形态

### 本地版（Gradio）

适合个人作者在本机直接使用，开箱即用。

```bash
python run.py
# 访问 http://127.0.0.1:7860
```

### 商业版（Vue 3 + FastAPI）

面向多用户、管理员后台、会员体系和后台任务场景。

```bash
# Windows
start-commercial.bat

# Linux / macOS
chmod +x start-commercial.sh && ./start-commercial.sh
```

默认地址：前端 `http://127.0.0.1:4173` | 后端 `http://127.0.0.1:8000` | API文档 `http://127.0.0.1:8000/docs`

---

## 核心功能

### 创作引擎

| 功能 | 说明 |
|------|------|
| 雪花法规划 | 从核心创意到完整大纲的分层展开 |
| 章节蓝图 | 每章的情节节点、角色弧线和场景设定 |
| 单章生成 | 基于上下文的章节内容生成 |
| 整本生成 | 后台任务自动生成完整小说 |
| 润色优化 | 风格化改写，去AI味 |
| 续写扩展 | 基于现有内容继续创作 |
| 连贯性分析 | 跨章节的剧情、角色、设定一致性检测 |

### 商业版特性

| 功能 | 说明 |
|------|------|
| 用户系统 | 注册、登录、JWT认证 |
| 角色权限 | 管理员 / 运营 / 客服 / 客户分层 |
| 会员体系 | 等级管理、配额控制、卡密兑换 |
| 支付系统 | 订单、账单、支付网关（含人工转账通道） |
| 管理后台 | 用户管理、卡密管理、订单管理、系统配置、提示词管理、审计日志 |
| 项目隔离 | 按用户隔离项目数据 |

### 模型支持

支持 20+ 主流 API 提供商（OpenAI、Claude、Gemini、通义千问、文心一言、DeepSeek 等），管理员统一配置，客户端开箱即用。

---

## 快速开始

### 环境要求

- Python 3.10+
- Node.js 18+（商业版前端）
- pip 包管理器

### 安装

```bash
# 克隆项目
git clone https://github.com/yangqi1309134997-coder/ai-novel-generator.git
cd ai-novel-generator

# 安装依赖
pip install -r requirements.txt

# 商业版额外安装前端
cd frontend-web
npm install
```

### 启动

| 版本 | 命令 | 地址 |
|------|------|------|
| 本地版 | `python run.py` | http://127.0.0.1:7860 |
| 商业版 | `start-commercial.bat` | http://127.0.0.1:4173 |

### 环境变量

复制 `.env.example` 为 `.env`，按需配置：

```bash
cp .env.example .env
```

主要配置项：后端端口、CORS、支付密钥、人工转账账户信息、数据库路径等。

---

## 项目结构

```
ai-novel-generator/
├── backend/              # FastAPI 后端（商业版）
│   ├── core/             # 安全、配置、设置
│   ├── models/           # ORM 模型
│   ├── routers/          # API 路由
│   ├── schemas/          # Pydantic 模型
│   ├── services/         # 业务逻辑
│   └── utils/            # 工具函数
├── frontend-web/         # Vue 3 前端（商业版）
│   └── src/
│       ├── views/        # 页面视图
│       ├── components/   # 通用组件
│       └── api/          # API 客户端
├── src/                  # 核心引擎（本地版 + 共用）
│   ├── api/              # API 客户端
│   ├── config/           # 配置管理
│   ├── core/             # 生成引擎、评估器、提示词
│   └── ui/               # Gradio 界面
├── config/               # 配置文件
│   ├── generation_config.json
│   ├── custom_prompts.json
│   └── style_prompts/    # 风格提示词模板
├── templates/            # 基础模板
├── docs/                 # 文档
└── scripts/              # 工具脚本
```

---

## 文档

| 文档 | 说明 |
|------|------|
| [更新日志](docs/CHANGELOG.md) | 版本更新记录 |
| [用户手册](docs/USER_MANUAL.md) | 完整使用指南 |
| [API 参考](docs/API_REFERENCE.md) | 后端 API 文档 |
| [依赖说明](docs/DEPENDENCIES.md) | 项目依赖清单 |
| [提示词优化指南](docs/PROMPT_OPTIMIZATION_GUIDE.md) | 提示词调优方法 |
| [优化速查](docs/OPTIMIZATION_QUICKSTART.md) | 常用优化配置 |
| [完整提示词参考](docs/COMPLETE_PROMPT_REFERENCE.md) | 所有内置提示词模板 |

---

## 测试

```bash
# 后端单元测试
pytest tests/backend/

# 商业版 API 回归
python scripts/commercial_api_regression.py
```

---

## 许可证

MIT License，详见 [LICENSE](LICENSE)。
