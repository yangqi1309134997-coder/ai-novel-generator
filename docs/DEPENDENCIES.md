# 依赖管理说明

> 依赖基线说明
>
> 本文档主要描述 Python / 本地版依赖管理思路。
> 当前仓库已经同时包含商业版前后端，商业版依赖还包括：
>
> - 前端：`frontend-web/package.json`
> - 商业版后端补充依赖：`backend/requirements.txt`
>
> 如果你在处理商业版发布或验收，请优先同时检查：
>
> - `pyproject.toml`
> - `frontend-web/package.json`
> - `backend/requirements.txt`

## 概述

本项目使用多种方式管理 Python 依赖，以适应不同的使用场景：

| 文件 | 用途 | 版本策略 |
|------|------|----------|
| `requirements.txt` | 生产依赖 | 灵活版本范围 (`>=X.Y.Z,<A.B.C`) |
| `requirements-dev.txt` | 开发依赖 | 包含生产依赖 + 开发工具 |
| `requirements.lock` | 生产锁定版本 | 精确版本 (`==X.Y.Z`) |
| `pyproject.toml` | 项目元数据 | 现代 Python 项目标准 |

## 快速开始

### 生产环境安装

```bash
# 使用灵活版本（推荐）
pip install -r requirements.txt

# 或使用锁定版本（完全复现）
pip install -r requirements.lock
```

### 开发环境安装

```bash
# 安装所有开发依赖
pip install -r requirements-dev.txt

# 或使用 pip 安装
pip install -e ".[dev]"
```

## 核心依赖说明

### gradio (>=4.44.0,<5.0.0)
- **用途**: Web UI 框架
- **为什么需要**: 构建用户交互界面
- **注意事项**: Gradio 5.0 可能有破坏性更改，因此限制在 4.x

### openai (>=1.54.0,<2.0.0)
- **用途**: OpenAI API SDK
- **为什么需要**: 调用 LLM API（支持 20+ 兼容 OpenAI 格式的提供商）
- **注意事项**: OpenAI SDK 2.0 可能有 API 变更

### python-docx (>=1.1.2,<2.0.0)
- **用途**: Word 文档处理
- **为什么需要**:
  - 润色功能：读取 `.docx` 文件
  - 导出功能：生成 Word 格式输出
- **可选**: 如果不需要处理 Word 文档，可以不安装

## 间接依赖

以下依赖由核心依赖自动安装，无需手动指定：

- **httpx, httpcore**: HTTP 客户端
- **aiohttp**: 异步 HTTP 支持
- **pandas, numpy**: 数据处理（Gradio Dataframe 组件）
- **pillow**: 图像处理
- **python-multipart**: 文件上传支持
- **pydantic**: 数据验证

## 版本策略

### 语义化版本约定

```
X.Y.Z  # 主版本.次版本.补丁版本

> 1.2.3    # 大于 1.2.3 的任何版本
>= 1.2.3   # 大于或等于 1.2.3
< 2.0.0    # 小于 2.0.0
>= 1.2.3,< 2.0.0  # 1.2.3 到 2.0.0 之间
== 1.2.3   # 精确版本 1.2.3
~= 1.2.3   # 兼容版本（>= 1.2.3, < 1.3.0）
```

### 本项目策略

1. **生产依赖** (`requirements.txt`)
   - 使用 `>=X.Y.Z,<A.B.C` 范围
   - 允许小版本更新（安全补丁）
   - 防止破坏性更改

2. **锁定版本** (`requirements.lock`)
   - 使用精确版本 `==X.Y.Z`
   - 用于生产环境部署
   - 确保完全复现

## 更新依赖

### 安全更新

```bash
# 检查过时的包
pip list --outdated

# 更新所有包到兼容版本
pip install -r requirements.txt --upgrade

# 更新锁定文件
pip freeze > requirements.lock
```

### 单个包更新

```bash
# 更新 gradio 到最新兼容版本
pip install --upgrade 'gradio>=4.44.0,<5.0.0'
```

## 依赖审计

```bash
# 检查安全漏洞
pip check
pip-audit  # 需要安装: pip install pip-audit

# 查看依赖树
pip show gradio
pipdeptree  # 需要安装: pip install pipdeptree
```

## 常见问题

### Q: 为什么不用 poetry/pipenv？
A: 为了保持简单和兼容性，本项目使用传统的 `requirements.txt`。`pyproject.toml` 主要用于工具配置。

### Q: pandas 没有在 requirements.txt 中，为什么能用？
A: pandas 是 Gradio 的间接依赖，安装 Gradio 时会自动安装。

### Q: 如何减少安装包大小？
A: 可以使用 `pip install --no-deps` 只安装核心包，但需要手动处理间接依赖。

### Q: 如何在没有网络的环境安装？
A:
1. 在有网络的机器上下载 wheel 文件
2. 使用 `pip install --no-index --find-links=本地目录` 安装

## Python 版本要求

- **最低**: Python 3.9
- **推荐**: Python 3.11 或 3.12
- **测试**: 支持 Python 3.9, 3.10, 3.11, 3.12

## 许可证

所有依赖的许可证信息可以在 PyPI 上查看。
