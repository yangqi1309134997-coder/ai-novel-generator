# 🤝 AI 小说创作工具 - 贡献指南

> 欢迎来到 AI 小说创作工具项目的贡献指南！感谢您对开源项目的关注和支持。

## 📋 目录

- [贡献前必读](#贡献前必读)
- [开发环境设置](#开发环境设置)
- [项目结构说明](#项目结构说明)
- [代码规范](#代码规范)
- [开发流程](#开发流程)
- [测试指南](#测试指南)
- [文档贡献](#文档贡献)
- [Bug 报告和功能请求](#bug-报告和功能请求)
- [社区准则](#社区准则)
- [发布流程](#发布流程)
- [联系方式](#联系方式)

---

## 📖 贡献前必读

### 项目概述

**AI 小说创作工具 Pro** 是一个生产级别的智能小说创作系统，基于 Gradio 构建的现代化 Web 应用。该工具集成了先进的 AI 技术，为小说创作者提供从零开始创作、智能重写、多格式导出到项目管理的全流程解决方案。

**核心特性**：
- 🎯 **智能创作**: 从零开始创作长篇小说，支持自定义大纲和章节结构
- ✍️ **智能重写**: 上传已有小说文本，用多种风格进行高质量重写
- 📤 **多格式导出**: 支持 Word (.docx)、纯文本 (.txt)、Markdown (.md)、HTML (.html) 等多种格式
- 📂 **项目管理**: 完整的项目生命周期管理，支持断点续写和版本控制
- ⚙️ **灵活配置**: 支持多个 API 后端，细粒度的创作参数调整

### 开发环境要求

**系统要求**：
- **操作系统**: Windows 10+ / macOS 10.14+ / Ubuntu 18.04+
- **Python**: 3.8 或更高版本
- **内存**: 推荐 8GB 以上（用于更好的性能）
- **存储**: 至少 2GB 可用空间
- **网络**: 稳定的互联网连接（用于 AI API 调用）

**开发工具**：
- **IDE**: VS Code、PyCharm 或其他支持 Python 的编辑器
- **Git**: 版本控制
- **终端**: 命令行工具
- **浏览器**: 用于测试 Web 界面

---

## ⚙️ 开发环境设置

### Python 版本要求

```bash
# 检查 Python 版本
python --version
# 或
python3 --version

# 要求版本：Python 3.8+
# 示例输出：Python 3.9.7
```

### 虚拟环境配置

```bash
# 1. 克隆项目
git clone <repository-url>
cd ai小说生成工具正式版V3.0

# 2. 创建虚拟环境
python -m venv venv

# 3. 激活虚拟环境
# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate

# 4. 验证激活
(venv) $ echo $VIRTUAL_ENV  # Linux/Mac
(venv) C:\path\to\venv       # Windows
```

### 依赖安装

```bash
# 1. 安装核心依赖
pip install -r requirements.txt

# 2. 或手动安装核心依赖
pip install gradio>=4.0.0 pandas>=2.0.0 openai>=1.0.0 python-docx>=0.8.10

# 3. 安装可选依赖（推荐）
pip install PyMuPDF ebooklib beautifulsoup4 markdown

# 4. 安装开发依赖
pip install pytest black flake8 mypy pre-commit

# 5. 安装 pre-commit 钩子
pre-commit install
```

### 项目初始化

```bash
# 运行快速初始化脚本
python quickstart.py

# 该脚本将自动完成：
# ✅ 检查 Python 环境
# ✅ 创建必要目录结构
# ✅ 安装核心依赖包
# ✅ 生成默认配置文件
# ✅ 测试模块导入
```

### 环境变量配置

```bash
# 1. 复制环境变量模板
cp .env.template .env

# 2. 编辑 .env 文件
# 在 Windows 中：
NOVEL_TOOL_HOST=127.0.0.1
NOVEL_TOOL_PORT=7860
NOVEL_TOOL_SHOW_ERRORS=false
NOVEL_TOOL_CONCURRENCY=4
NOVEL_TOOL_QUEUE_MAX=50

# 在 Linux/Mac 中：
export NOVEL_TOOL_HOST=127.0.0.1
export NOVEL_TOOL_PORT=7860
export NOVEL_TOOL_SHOW_ERRORS=false
export NOVEL_TOOL_CONCURRENCY=4
export NOVEL_TOOL_QUEUE_MAX=50
```

---

## 📁 项目结构说明

```
ai小说生成工具正式版V3.0/
├── 📄 app.py                    # 主应用程序 - Gradio Web UI
├── 📄 config.py                # 配置管理模块
├── 📄 api_client.py            # API 调用客户端
├── 📄 novel_generator.py       # 小说生成核心逻辑
├── 📄 file_parser.py           # 文件解析模块
├── 📄 exporter.py              # 多格式导出模块
├── 📄 project_manager.py       # 项目管理模块
├── 📄 logger.py                # 日志管理模块
├── 📄 config_api.py            # 配置 API 接口
├── 📄 quickstart.py             # 快速开始脚本
├── 📄 requirements.txt         # Python 依赖列表
├── 📄 LICENSE                  # MIT 许可证
├── 📄 README.md                # 项目文档
├── 📄 CONTRIBUTING.md          # 贡献指南
├── 📁 config/                  # 配置文件目录
│   ├── 📄 novel_tool_config.json  # 主配置文件
│   └── 📄 backups/              # 配置备份目录
├── 📁 projects/                # 项目存储目录
├── 📁 exports/                 # 导出文件目录
├── 📁 logs/                    # 日志文件目录
├── 📁 cache/                   # 缓存文件目录
└── 📄 .env.template            # 环境变量模板
```

### 核心模块功能说明

#### [`app.py`](app.py:1) - 主应用程序
- **功能**: Gradio Web UI 的主入口点
- **职责**: 处理用户界面交互、事件绑定、状态管理
- **关键组件**: 
  - 生成状态管理（支持暂停/继续）
  - 多标签页界面（重写、创作、导出、设置等）
  - 项目管理功能集成

#### [`config.py`](config.py:1) - 配置管理模块
- **功能**: 系统配置的读取、验证和持久化
- **职责**: 
  - API 后端配置管理
  - 生成参数配置
  - 配置验证和备份
- **数据结构**: `Backend`, `GenerationConfig`, `ConfigManager`

#### [`novel_generator.py`](novel_generator.py:1) - 小说生成核心逻辑
- **功能**: AI 小说生成的核心业务逻辑
- **职责**: 
  - 大纲生成
  - 章节生成
  - 文本重写
  - 风格模板管理
- **关键类**: `NovelGenerator`, `OutlineParser`, `Chapter`

#### [`api_client.py`](api_client.py:1) - API 调用客户端
- **功能**: 统一的 AI API 调用接口
- **职责**: 
  - 多后端支持（OpenAI、Claude、Ollama等）
  - 负载均衡和故障转移
  - 缓存机制
  - 速率限制

#### [`file_parser.py`](file_parser.py:1) - 文件解析模块
- **功能**: 解析各种格式的输入文件
- **支持的格式**: TXT、PDF、EPUB
- **职责**: 文本提取和预处理

#### [`exporter.py`](exporter.py:1) - 多格式导出模块
- **功能**: 将小说内容导出为多种格式
- **支持的格式**: Word (.docx)、纯文本 (.txt)、Markdown (.md)、HTML (.html)
- **职责**: 格式转换和文件生成

#### [`project_manager.py`](project_manager.py:1) - 项目管理模块
- **功能**: 创作项目的生命周期管理
- **职责**: 
  - 项目创建、保存、加载
  - 项目元数据管理
  - 版本控制

#### [`logger.py`](logger.py:1) - 日志管理模块
- **功能**: 统一的日志记录系统
- **职责**: 
  - 分级日志记录
  - 性能监控
  - 错误追踪

---

## 📝 代码规范

### Python PEP 8 遵循

本项目严格遵循 [PEP 8](https://peps.python.org/pep-0008/) 编码规范：

```python
# ✅ 正确示例
def calculate_word_count(text: str) -> int:
    """计算文本字数"""
    if not text or not text.strip():
        return 0
    return len(text.strip())

# ❌ 错误示例
def calculate_word_count(text:str)->int:
    if not text or not text.strip():
        return 0
    return len(text.strip())
```

### 命名约定

#### 变量和函数
```python
# 使用下划线命名法
user_name = "张三"
calculate_total_words = lambda text: len(text)

# 私有成员使用下划线前缀
_internal_cache = {}
def _validate_config():
    pass
```

#### 类名
```python
# 使用 PascalCase（首字母大写）
class NovelGenerator:
    pass

class ConfigManager:
    pass
```

#### 常量
```python
# 使用全大写和下划线
MAX_FILE_SIZE = 50 * 1024 * 1024
DEFAULT_TIMEOUT = 30
```

### 注释规范

#### 文件头部注释
```python
"""
小说生成模块 - 支持大纲生成、章节生成、重写等

版权所有 © 2026 新疆幻城网安科技有限责任公司 (幻城科技)
作者：幻城
"""
```

#### 函数/方法注释
```python
def generate_chapter(
    self,
    chapter_num: int,
    chapter_title: str,
    chapter_desc: str,
    novel_title: str,
    character_setting: str,
    world_setting: str,
    plot_idea: str,
    previous_content: str = ""
) -> Tuple[str, str]:
    """
    生成单个章节
    
    Args:
        chapter_num: 章节编号
        chapter_title: 章节标题
        chapter_desc: 章节描述
        novel_title: 小说标题
        character_setting: 人物设定
        world_setting: 世界观设定
        plot_idea: 剧情想法
        previous_content: 前文内容（用于保证连贯性）
    
    Returns:
        Tuple[str, str]: (章节内容, 错误信息或成功提示)
    """
```

#### 行内注释
```python
# 使用简明的行内注释说明复杂逻辑
if not chapters or not chapters.strip():
    return [], "大纲为空"  # 空大纲处理

# 按章节号排序，确保生成顺序正确
chapters.sort(key=lambda x: x.num)
```

### 类型提示

所有函数和变量都应该使用类型提示：

```python
from typing import List, Dict, Optional, Tuple

def process_text(text: str) -> Optional[str]:
    """处理文本"""
    if not text:
        return None
    return text.strip()

def get_chapters() -> List[Dict]:
    """获取章节列表"""
    return []
```

### 代码格式化

使用 `black` 进行代码格式化：

```bash
# 格式化所有 Python 文件
black .

# 检查格式是否符合规范（不修改文件）
black --check .

# 设置行长度为 88 字符（默认）
black --line-length=88 .
```

### 代码检查

使用 `flake8` 进行代码质量检查：

```bash
# 检查所有文件
flake8 .

# 检查特定文件
flake8 app.py novel_generator.py

# 排除特定规则
flake8 --ignore=E203,W503 .
```

---

## 🔄 开发流程

### 分支管理

#### 分支命名规范

```bash
# 功能分支
feature/add-new-export-format
feature/improve-cache-mechanism
feature/rewrite-ui-components

# 修复分支
fix/resolve-api-timeout-issue
fix/corrupted-project-loading
fix/export-file-encoding

# 文档分支
docs/update-api-documentation
docs/contributing-guide

# 发布分支
release/v2.1.0
release/v2.0.0
```

#### 分支操作流程

```bash
# 1. 从 main 分支创建功能分支
git checkout main
git pull origin main
git checkout -b feature/your-feature-name

# 2. 开发过程中定期提交
git add .
git commit -m "feat: add new export format support"

# 3. 推送到远程仓库
git push origin feature/your-feature-name

# 4. 创建 Pull Request
# 在 GitHub/GitLab 界面上创建 PR，填写详细信息
```

### 提交规范

#### 提交消息格式

使用 [Conventional Commits](https://www.conventionalcommits.org/) 规范：

```bash
# 格式：<类型>(<范围>): <描述>
# 
# 类型：
# feat: 新功能
# fix: 修复 bug
# docs: 文档更新
# style: 代码格式化
# refactor: 重构
# test: 测试相关
# chore: 构建或工具变动

# 示例：
feat(generator): add support for custom writing styles
fix(api): resolve timeout issue with large requests
docs(readme): update installation instructions
style(format): apply black formatting to all files
test(unit): add tests for chapter generation
chore(deps): update gradio to latest version
```

#### 提交消息模板

```bash
# .gitmessage.txt 文件模板
# feat: (新增功能)
# fix: (修复bug)
# docs: (文档更新)
# style: (代码格式化)
# refactor: (重构)
# test: (测试)
# chore: (构建或工具变动)

# 短描述 (50字符以内，限制在72字符)

# 详细描述 (可选)
# 涉及的功能模块
# 解决的问题
# 实现方案

# 关联的 Issue (可选)
# Fixes #123
# Related to #456
```

### Pull Request 流程

#### PR 模板

```markdown
## 变更描述
简要描述这个 PR 的主要变更内容

## 变更类型
- [ ] Bug 修复
- [ ] 新功能
- [ ] 文档更新
- [ ] 代码重构
- [ ] 性能优化
- [ ] 其他

## 测试清单
- [ ] 功能测试通过
- [ ] 单元测试通过
- [ ] 集成测试通过
- [ ] 手动测试通过

## 破坏性变更
- [ ] 是 (请说明)
- [ ] 否

## 相关 Issue
- Fixes #123
- Related to #456

## 截图（如适用）
<!-- 添加相关功能的截图 -->

## 其他说明
<!-- 补充其他需要说明的信息 -->
```

#### PR 审查流程

```bash
# 1. 创建 PR 后的自检清单
□ 代码符合项目规范
□ 添加了必要的测试
□ 更新了相关文档
□ 提交消息规范
□ 分支名称规范

# 2. 等待审查
- 等待至少一名维护者审查
- 根据审查意见进行修改
- 确保所有 CI/CD 检查通过

# 3. 合并 PR
- 获得批准后，可以合并
- 确保没有冲突
- 合并后删除分支
```

### 版本控制最佳实践

```bash
# 1. 保持提交原子性
# 每个提交只做一件事

# 2. 定期同步主分支
git checkout main
git pull origin main
git checkout feature/your-branch
git rebase main

# 3. 解决冲突后继续
git add .
git rebase --continue

# 4. 推送到远程前检查
git status
git diff
git log --oneline -5
```

---

## 🧪 测试指南

### 测试结构

```
tests/
├── __init__.py
├── test_config.py
├── test_novel_generator.py
├── test_api_client.py
├── test_exporter.py
├── test_project_manager.py
├── integration/
│   ├── test_full_workflow.py
│   └── test_api_integration.py
└── fixtures/
    └── sample_config.json
```

### 单元测试

#### 测试配置模块

```python
# tests/test_config.py
import pytest
from config import ConfigManager, Backend, GenerationConfig

def test_backend_validation():
    """测试后端配置验证"""
    # 有效配置
    valid_backend = Backend(
        name="test-api",
        type="openai",
        base_url="https://api.openai.com/v1",
        api_key="test-key",
        model="gpt-4"
    )
    assert valid_backend.validate() == (True, "OK")
    
    # 无效配置
    invalid_backend = Backend(
        name="",
        type="invalid",
        base_url="invalid-url",
        api_key="",
        model=""
    )
    assert invalid_backend.validate()[0] == False

def test_generation_config():
    """测试生成配置"""
    config = GenerationConfig()
    assert config.temperature == 0.7
    assert config.chapter_target_words == 2500
    
    # 测试参数验证
    config.temperature = 2.5  # 超出范围
    assert config.validate()[0] == False
```

#### 测试小说生成器

```python
# tests/test_novel_generator.py
import pytest
from novel_generator import NovelGenerator, OutlineParser

def test_outline_parser():
    """测试大纲解析器"""
    outline_text = """
    第1章: 开篇 - 介绍主人公和世界观
    第2章: 冲突 - 主人公遇到第一个重大挑战
    第3章: 转折 - 意外改变命运走向
    """
    
    chapters, msg = OutlineParser.parse(outline_text)
    assert len(chapters) == 3
    assert chapters[0].title == "开篇"
    assert chapters[0].desc == "介绍主人公和世界观"

def test_generator_initialization():
    """测试生成器初始化"""
    generator = NovelGenerator()
    assert generator.config is not None
    assert generator.api_client is not None
```

### 集成测试

#### API 集成测试

```python
# tests/integration/test_api_integration.py
import pytest
from api_client import get_api_client

@pytest.fixture
def api_client():
    """API 客户端 fixture"""
    return get_api_client()

def test_api_connection(api_client):
    """测试 API 连接"""
    # 使用测试后端
    backends = api_client.get_backends()
    test_backend = next((b for b in backends if b.name == "test-backend"), None)
    
    if test_backend:
        success, result = api_client.test_backend(test_backend.name)
        assert success == True
```

#### 完整工作流测试

```python
# tests/integration/test_full_workflow.py
import pytest
from novel_generator import NovelGenerator
from project_manager import ProjectManager

def test_full_creation_workflow():
    """测试完整的创作工作流"""
    generator = NovelGenerator()
    
    # 生成大纲
    outline, status = generator.generate_outline(
        title="测试小说",
        genre="玄幻",
        total_chapters=5,
        character_setting="测试角色",
        world_setting="测试世界观",
        plot_idea="测试剧情"
    )
    
    assert outline != ""
    assert "成功" in status
    
    # 解析大纲
    chapters, parse_msg = OutlineParser.parse(outline)
    assert len(chapters) == 5
    
    # 生成章节
    content, gen_status = generator.generate_chapter(
        chapter_num=1,
        chapter_title=chapters[0].title,
        chapter_desc=chapters[0].desc,
        novel_title="测试小说",
        character_setting="测试角色",
        world_setting="测试世界观",
        plot_idea="测试剧情"
    )
    
    assert content != ""
    assert "成功" in gen_status
```

### 测试运行方法

#### 运行所有测试

```bash
# 运行所有测试
pytest

# 运行并显示覆盖率
pytest --cov=. --cov-report=html

# 运行特定测试文件
pytest tests/test_config.py

# 运行特定测试函数
pytest tests/test_config.py::test_backend_validation

# 运行测试并生成报告
pytest --junitxml=test-results.xml
```

#### 测试覆盖率要求

```bash
# 覆盖率检查
pytest --cov=. --cov-report=term-missing

# 要求：
# - 核心模块覆盖率 > 80%
# - 新功能覆盖率 > 90%
# - 关键路径覆盖率 = 100%
```

#### 持续集成测试

```yaml
# .github/workflows/test.yml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: [3.8, 3.9, "3.10", "3.11"]
    
    steps:
    - uses: actions/checkout@v3
    - name: Set up Python ${{ matrix.python-version }}
      uses: actions/setup-python@v3
      with:
        python-version: ${{ matrix.python-version }}
    
    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install -r requirements.txt
        pip install pytest pytest-cov
    
    - name: Run tests
      run: |
        pytest --cov=. --cov-report=xml
    
    - name: Upload coverage
      uses: codecov/codecov-action@v3
```

---

## 📚 文档贡献

### 文档类型

#### 1. 代码文档
- **模块文档**: 每个模块的头部注释
- **函数文档**: 所有公共函数的详细文档
- **类文档**: 所有公共类的文档
- **内联注释**: 复杂逻辑的解释

#### 2. 用户文档
- **README.md**: 项目概述和快速开始
- **用户手册**: 详细的使用指南
- **API 文档**: 接口使用说明
- **配置指南**: 配置选项说明

#### 3. 开发文档
- **CONTRIBUTING.md**: 贡献指南
- **ARCHITECTURE.md**: 系统架构说明
- **DEVELOPMENT.md**: 开发环境搭建
- **CHANGELOG.md**: 版本变更记录

### 文档编写规范

#### Markdown 格式规范

```markdown
# 一级标题
## 二级标题
### 三级标题

**粗体文本**
*斜体文本*
`代码文本`

- 无序列表项
- 另一个列表项

1. 有序列表项
2. 另一个列表项

```python
# 代码块
def example_function():
    return "Hello, World!"
```

> 引用文本

[链接文本](https://example.com)
```

#### API 文档格式

```python
def generate_novel_outline(
    title: str,
    genre: str,
    total_chapters: int,
    character_setting: str,
    world_setting: str,
    plot_idea: str
) -> Tuple[str, str]:
    """
    生成小说大纲
    
    Args:
        title (str): 小说标题
        genre (str): 小说类型（如：玄幻、都市、科幻等）
        total_chapters (int): 章节总数
        character_setting (str): 人物设定描述
        world_setting (str): 世界观设定描述
        plot_idea (str): 主线剧情想法
    
    Returns:
        Tuple[str, str]: (大纲文本, 状态信息)
            - 大纲文本: 生成的小说大纲
            - 状态信息: 成功/失败信息
    
    Raises:
        ValueError: 当输入参数无效时
    
    Example:
        >>> outline, status = generate_novel_outline(
        ...     title="修仙之路",
        ...     genre="玄幻",
        ...     total_chapters=20,
        ...     character_setting="主角资质平平但心性坚韧",
        ...     world_setting="修真世界，宗门林立",
        ...     plot_idea="从凡人到强者的成长之路"
        ... )
        >>> print(outline)
        第1章: 凡尘少年 - 主角出身平凡，展现不凡天赋
        第2章: 宗门测试 - 通过测试，获得入门资格...
    """
```

### 文档更新流程

#### 文档修改检查清单

```markdown
□ 新功能添加了相应的文档
□ 修改的功能更新了文档
□ API 接口文档保持最新
□ 代码示例正确可用
□ 文档格式符合规范
□ 拼写和语法检查通过
```

#### 文档测试

```bash
# 检查文档中的代码示例
python -m doctest README.md -v

# 验证 Markdown 语法
pip install markdown
python -m markdown README.md > /dev/null

# 检查链接有效性
pip install linkcheck
markdown-linkcheck README.md
```

### 文档贡献示例

#### 添加新功能文档

```markdown
## 新功能：自定义导出格式

### 概述
新增了对自定义导出格式的支持，允许用户定义自己的导出模板。

### 使用方法

#### 基本用法

```python
from exporter import export_custom

# 使用自定义模板导出
success, message = export_custom(
    content="小说内容",
    title="我的小说",
    template="custom_template.json"
)
```

#### 自定义模板格式

```json
{
  "name": "自定义格式",
  "extension": ".custom",
  "template": {
    "header": "# {{title}}\n\n",
    "content": "{{content}}\n",
    "footer": "\n---\n生成时间：{{timestamp}}"
  }
}
```

### 注意事项
- 模板文件必须是有效的 JSON 格式
- 支持的变量：`{{title}}`, `{{content}}`, `{{timestamp}}`
- 请确保模板不会导致安全风险
```

---

## 🐛 Bug 报告和功能请求

### Bug 报告格式

#### Bug 报告模板

```markdown
## Bug 描述
简要描述遇到的问题

## 复现步骤
1. 执行操作 A
2. 点击按钮 B
3. 输入文本 C
4. 观察结果

## 期望行为
描述应该发生什么

## 实际行为
描述实际发生了什么

## 环境信息
- 操作系统: [例如：Windows 11]
- Python 版本: [例如：3.9.7]
- 项目版本: [例如：v2.0.0]
- 浏览器: [如果涉及 Web 界面]

## 错误信息
```
粘贴完整的错误信息
```

## 截图（可选）
![截图描述](screenshot-url)

## 其他信息
任何其他有助于理解问题的信息
```

#### Bug 报告示例

```markdown
## Bug 描述
导出为 Word 文档时，中文标点符号显示异常

## 复现步骤
1. 生成一篇包含中文标点的小说
2. 切换到"导出与分享"标签页
3. 选择"导出为 Word (.docx)"
4. 点击导出按钮

## 期望行为
中文标点符号（，。！？）应该正常显示

## 实际行为
中文标点符号显示为乱码或问号

## 环境信息
- 操作系统: Windows 11
- Python 版本: 3.9.7
- 项目版本: v2.0.0
- 浏览器: Chrome 96.0

## 错误信息
```
Traceback (most recent call last):
  File "exporter.py", line 45, in export_to_docx
    doc.add_paragraph(content)
  File "python-docx-0.8.11/docx/text/paragraph.py", line 45, in add_paragraph
    return Paragraph(p, self)
  File "python-docx-0.8.11/docx/text/paragraph.py", line 25, in __init__
    self._p = p
UnicodeEncodeError: 'ascii' codec can't encode characters in position 123-125: ordinal not in range(128)
```

## 截图
![导出Word文档标点异常](https://example.com/screenshot.png)

## 其他信息
这个问题只在导出中文内容时出现，英文内容导出正常。
```

### 功能请求格式

#### 功能请求模板

```markdown
## 功能描述
详细描述您希望添加的功能

## 问题背景
说明为什么需要这个功能，解决了什么问题

## 建议的实现方案
描述您认为如何实现这个功能

## 使用场景
描述这个功能的使用场景和用户故事

## 优先级
- [ ] 低 - 改善性功能
- [ ] 中 - 有用功能
- [ ] 高 - 重要功能
- [ ] 紧急 - 阻塞性问题

## 相关信息
任何其他相关信息或建议
```

#### 功能请求示例

```markdown
## 功能描述
添加批量导出功能，支持一次性导出多个项目

## 问题背景
当前每次只能导出一个项目，当用户有多个项目需要导出时，操作重复且效率低下。

## 建议的实现方案
1. 在项目管理页面添加"批量选择"功能
2. 添加"批量导出"按钮
3. 支持选择多个项目并指定统一导出格式
4. 自动下载所有导出文件到压缩包

## 使用场景
用户完成了多个小说项目，需要将它们全部导出为 PDF 格式进行备份或分享。

## 优先级
- [ ] 低 - 改善性功能
- [x] 中 - 有用功能
- [ ] 高 - 重要功能
- [ ] 紧急 - 阻塞性问题

## 相关信息
可以考虑添加导出进度显示和取消功能。
```

### 问题报告最佳实践

#### 信息收集清单

```markdown
□ 问题描述清晰明确
□ 复现步骤具体详细
□ 期望行为和实际行为对比
□ 环境信息完整准确
□ 错误信息完整（包括堆栈跟踪）
□ 截图或录屏（如适用）
□ 尝试过的解决方案
□ 相关日志文件
```

#### 调试信息收集

```bash
# 收集系统信息
python -c "import sys; print('Python:', sys.version); import platform; print('OS:', platform.platform())"

# 检查依赖版本
pip list | grep -E "(gradio|pandas|openai|python-docx)"

# 查看项目日志
tail -f logs/novel_tool_*.log

# 检查配置文件
cat config/novel_tool_config.json
```

---

## 👥 社区准则

### 礼貌沟通

#### 交流基本原则

```markdown
✅ 尊重每个人的贡献和观点
✅ 使用清晰、专业的语言
✅ 积极倾听和理解他人的意见
✅ 专注于技术讨论和问题解决
✅ 对新手友好，耐心解答问题

❌ 避免人身攻击或贬低言论
❌ 不要发表歧视性或冒犯性内容
❌ 避免无意义的争论和争吵
❌ 不要刷屏或发布垃圾信息
❌ 尊重他人的时间和精力
```

#### 交流示例

```markdown
# ✅ 好的提问方式

"我在尝试添加新的导出格式时遇到了问题。我已经实现了基本的导出函数，但在处理特殊字符时出现了编码错误。以下是我的代码：

```python
def export_to_custom(content: str, title: str):
    # 我的实现
    pass
```

错误信息是：`UnicodeEncodeError: 'ascii' codec can't encode...`

有人能帮我看看这个问题吗？我已经检查了文档，但没找到相关的编码处理说明。"

# ❌ 不好的提问方式

"这个项目文档太烂了！我按照文档做根本不行！你们这些人写代码的时候都不测试的吗？"
```

### 尊重他人

#### 贡献者尊重

```markdown
# 对代码贡献者
- 感谢他人的时间和努力
- 提供建设性的反馈
- 关注代码质量而非个人
- 承认他人的贡献

# 对用户
- 耐心解答用户问题
- 理解用户的技能水平差异
- 提供清晰的使用指导
- 尊重用户的使用场景

# 对维护者
- 理解维护者的工作量
- 遵循项目的既定流程
- 给予维护者足够的响应时间
- 感谢维护者的持续维护
```

### 建设性反馈

#### 反馈原则

```markdown
# 给予反馈时
- 具体而非模糊
- 关注事实而非观点
- 提供改进建议
- 保持友善和尊重
- 考虑对方的接受度

- 接受反馈时
- 保持开放心态
- 认真倾听反馈内容
- 感谢反馈者的时间
- 理解反馈的价值
- 有选择地采纳建议
```

#### 反馈示例

```markdown
# ✅ 建设性反馈

"我注意到在 `novel_generator.py` 中的 `generate_chapter` 函数，当前的实现可能会导致内存使用过高，特别是对于长篇小说。建议可以考虑：

1. 添加流式生成支持
2. 实现章节分块处理
3. 优化内存管理

我可以提供一个实现方案，您觉得如何？"

# ❌ 非建设性反馈

"这个函数写得真烂！内存占用这么高，根本不能用！"
```

### 冲突解决

#### 处理分歧

```markdown
# 当出现分歧时
1. 保持冷静和专业
2. 专注于技术问题而非个人
3. 寻找共同点
4. 提供数据和事实支持
5. 寻求第三方意见
6. 必要时寻求维护者介入

# 冲突升级流程
1. 直接沟通 → 2. 团队讨论 → 3. 维护者调解 → 4. 社区投票 → 5. 项目决策
```

### 包容性环境

#### 多样性尊重

```markdown
# 我们欢迎
- 不同技术背景的贡献者
- 不同经验水平的开发者
- 不同文化背景的用户
- 不同观点的讨论
- 女性和少数群体参与

# 我们反对
- 技术歧视和偏见
- 经验歧视和偏见
- 文化歧视和偏见
- 性别歧视和偏见
- 任何形式的歧视
```

---

## 🚀 发布流程

### 版本号规范

#### 语义化版本 (SemVer)

遵循 [语义化版本 2.0.0](https://semver.org/) 规范：

```
主版本号.次版本号.修订号
MAJOR.MINOR.PATCH
```

#### 版本号含义

```markdown
# 主版本号 (MAJOR)
- 当有破坏性变更时递增
- 例如：1.0.0 → 2.0.0

# 次版本号 (MINOR)  
- 当添加向后兼容的新功能时递增
- 例如：1.0.0 → 1.1.0

# 修订号 (PATCH)
- 当进行向后兼容的修复时递增
- 例如：1.0.0 → 1.0.1
```

#### 版本号示例

```markdown
# 功能发布
v2.0.0 → v2.1.0  # 添加批量导出功能
v2.1.0 → v2.2.0  # 添加新的写作风格模板

# Bug 修复
v2.1.0 → v2.1.1  # 修复导出中文标点符号问题
v2.2.0 → v2.2.1  # 修复项目保存失败问题

# 破坏性变更
v2.0.0 → v3.0.0  # 重构配置系统（不兼容旧版本）
```

### 发布检查清单

#### 发布前检查

```markdown
## 代码质量
- [ ] 所有测试通过
- [ ] 代码覆盖率达标
- [ ] 代码风格检查通过
- [ ] 静态分析无警告

## 文档更新
- [ ] 更新 CHANGELOG.md
- [ ] 更新 README.md（如适用）
- [ ] 更新 API 文档（如适用）
- [ ] 更新安装说明

## 功能验证
- [ ] 新功能测试通过
- [ ] 旧功能回归测试通过
- [ ] 性能测试通过
- [ ] 安全测试通过

## 发布准备
- [ ] 版本号正确设置
- [ ] 发布说明已准备
- [ ] 二进制文件已构建（如适用）
- [ ] 文档已部署
```

#### 发布流程步骤

```bash
# 1. 准备发布
git checkout main
git pull origin main

# 2. 更新版本号
# 在 config.py 中更新版本
vim config.py

# 3. 更新 CHANGELOG.md
vim CHANGELOG.md

# 4. 提交变更
git add .
git commit -m "release: v2.1.0"

# 5. 创建标签
git tag -a v2.1.0 -m "Release v2.1.0"

# 6. 推送到远程
git push origin main
git push origin v2.1.0

# 7. 创建发布分支（可选）
git checkout -b release/v2.1.0-hotfixes
```

### 更新日志维护

#### CHANGELOG.md 格式

```markdown
# 更新日志

所有重要的变更都会记录在此文件中。

本项目遵循 [语义化版本](https://semver.org/lang/zh-CN/) 规范。

## [2.1.0] - 2024-01-15

### 新增
- 🎯 批量导出功能，支持一次性导出多个项目
- 📝 新增 5 种写作风格模板
- 🔧 添加配置文件导入导出功能
- 🌐 支持自定义主题和界面样式

### 改进
- ⚡ 优化大文件处理性能，提升 30%
- 🔍 改进大纲解析器，支持更多格式
- 📊 添加详细的性能监控面板
- 🛡️ 增强错误处理和恢复机制

### 修复
- 🐛 修复中文标点符号导出异常问题
- 🐛 修复项目保存时的并发问题
- 🐛 修复某些 API 后端的连接超时问题
- 🐛 修复界面在某些浏览器中的显示问题

### 文档
- 📚 更新 API 文档和示例
- 📚 添加批量导出使用指南
- 📚 改进安装和配置说明

## [2.0.0] - 2023-12-01

### 新增
- 🎯 完整的小说创作工作流
- ✍️ 智能重写功能
- 📤 多格式导出支持
- 📂 项目管理系统
- ⚙️ 灵活的配置管理

### 破坏性变更
- 重构配置系统，不兼容 v1.x 版本
- 更新最低 Python 版本要求到 3.8
- 修改 API 接口参数结构
```

#### 更新日志编写规范

```markdown
# 使用表情符号分类
✨ 新增功能 (New Feature)
🐛 Bug 修复 (Bug Fix)
🚀 性能优化 (Performance Improvement)
🔧 代码重构 (Refactoring)
📚 文档更新 (Documentation)
🎨 样式更新 (Styling)
♻️ 代码优化 (Code Optimization)
🔒 安全更新 (Security Update)
💡 改进功能 (Improvement)
🗑️ 移除功能 (Removed)

# 描述格式
- 简洁明了的描述
- 说明解决的问题
- 提供使用示例（如适用）
```

### 发布后跟进

#### 发布验证

```bash
# 1. 验证发布
# 检查 GitHub Release 是否正确创建
# 检查 PyPI 包是否已上传（如适用）
# 检查文档是否已更新

# 2. 收集反馈
# 监控 Issues 和 Discussions
# 收集用户反馈
# 准备后续修复计划

# 3. 发布公告
# 在社区发布公告
# 更新社交媒体
# 发送邮件通知（如适用）
```

#### 紧急修复流程

```bash
# 1. 创建修复分支
git checkout main
git pull origin main
git checkout -b hotfix/issue-123

# 2. 应用修复
# 修复代码
git add .
git commit -m "fix: resolve critical issue #123"

# 3. 测试修复
pytest
# 手动测试

# 4. 创建紧急发布
git tag -a v2.1.1-hotfix -m "Hotfix: v2.1.1"
git push origin hotfix/issue-123
git push origin v2.1.1-hotfix

# 5. 合并到主分支
git checkout main
git merge hotfix/issue-123
git push origin main
```

---

## 📞 联系方式

### 技术支持

#### 官方渠道

```markdown
# GitHub Issues
- 用途：Bug 报告、功能请求、问题咨询
- 链接：[GitHub Issues](https://github.com/your-repo/issues)
- 响应时间：通常 24-48 小时

# GitHub Discussions  
- 用途：功能讨论、使用交流、经验分享
- 链接：[GitHub Discussions](https://github.com/your-repo/discussions)
- 响应时间：通常 12-24 小时

# 邮件支持
- 邮箱：support@noveltool.com
- 用途：商业合作、技术咨询、紧急问题
- 响应时间：通常 8-12 小时（工作日）
```

#### 社区支持

```markdown
# QQ 群
- 群号：123456789
- 用途：实时交流、问题解答
- 活跃时间：每日 9:00-22:00

# 微信群
- 请添加技术支持微信：NovelTool-Support
- 用途：用户交流、功能反馈
- 验证信息：AI小说创作工具

# 开发者社区
- 论坛：https://forum.noveltool.com
- 用途：深度技术讨论、插件开发
```

### 问题咨询

#### 常见问题分类

```markdown
# 安装配置问题
- 环境要求不满足
- 依赖包安装失败
- 配置文件错误
- 权限问题

# 功能使用问题  
- 界面操作不熟悉
- 功能使用方法
- 参数配置建议
- 导出格式选择

# 技术开发问题
- API 集成问题
- 自定义开发
- 源码编译
- 性能优化

# 商业合作问题
- 定制开发需求
- 技术支持服务
- 商业授权咨询
- 合作洽谈
```

#### 联系信息更新

```markdown
# 维护者信息
- **主要维护者**: 幻城
- **所属公司**: 新疆幻城网安科技有限责任公司
- **技术负责**: tech@noveltool.com
- **商务联系**: business@noveltool.com

# 社区管理员
- **社区负责人**: CommunityManager
- **活动组织**: events@noveltool.com
- **文档维护**: docs@noveltool.com

# 紧急联系
- **技术支持热线**: 400-123-4567（工作日 9:00-18:00）
- **紧急故障**: emergency@noveltool.com
```

---

## 🎉 结语

感谢您对 AI 小说创作工具项目的关注和贡献！您的参与让这个项目变得更好。

### 贡献者荣誉墙

```markdown
# 核心贡献者
- 幻城 - 项目架构设计与核心开发
- [您的名字将在这里...]

# 特别感谢
感谢所有提交 Issue、PR、文档改进和功能建议的贡献者！

# 如何成为贡献者
1. Fork 项目仓库
2. 创建功能分支
3. 提交您的改进
4. 创建 Pull Request
5. 参与代码审查

# 一起成长
每一个小贡献都很重要，让我们一起构建更好的 AI 创作工具！
```

---

**最后更新**: 2024年1月  
**维护者**: 幻城  
**许可证**: MIT License