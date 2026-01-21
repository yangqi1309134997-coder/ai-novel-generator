# 📚 AI 小说创作工具 Pro

> 生产级别的智能小说创作系统 v2.0

![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)
![Gradio](https://img.shields.io/badge/Gradio-Web%20UI-green.svg)
![License](https://img.shields.io/badge/License-MIT-yellow.svg)

## 🌟 项目简介

AI 小说创作工具 Pro 是一个基于 Gradio 构建的现代化 Web 应用，专为小说创作者打造。集成了先进的 AI 技术，提供从零开始创作、智能重写、多格式导出到项目管理的全流程解决方案。
有任何问题请加qq群进行反馈，由于前期比较赶工，有好多没做到位的一些小Bug，现在正在全力修复，加入交流群进行反馈，需要哪些功能也进行反馈qq群号：253193620
##网盘下载链接
我用夸克网盘分享了「ai-novel-generator--version-v4.0.zip」，点击链接即可保存。打开「夸克APP」，无需下载在线播放视频，畅享原画5倍速，支持电视投屏。
链接：https://pan.quark.cn/s/e2e6872b940d

通过网盘分享的文件：ai-novel-generator--version-v4.0.zip
链接: https://pan.baidu.com/s/1NZsNkpsFKRByNBDakB3jyw?pwd=5g9a 提取码: 5g9a 
--来自百度网盘超级会员v4的分享

### 核心特性

- 🎯 **智能创作**: 从零开始创作长篇小说，支持自定义大纲和章节结构
- ✍️ **智能重写**: 上传已有小说文本，用多种风格进行高质量重写
- 📤 **多格式导出**: 支持 Word (.docx)、纯文本 (.txt)、Markdown (.md)、HTML (.html) 等多种格式
- 📂 **项目管理**: 完整的项目生命周期管理，支持断点续写和版本控制
- ⚙️ **灵活配置**: 支持多个 API 后端，细粒度的创作参数调整

## 🚀 快速开始

### 系统要求

- **Python**: 3.8 或更高版本
- **操作系统**: Windows / macOS / Linux
- **内存**: 推荐 4GB 以上
- **存储**: 至少 1GB 可用空间

### 安装步骤

1. **克隆项目**
```bash
[git clone <repository-url>](https://github.com/yangqi1309134997-coder/ai-novel-generator.git)
cd 目录
```

## 🚀 使用方法

### 基本使用

在项目根目录下运行：

```bash
python start_venv.py
```

### Windows系统

在PowerShell或CMD中：

```powershell
python start_venv.py
```

### Linux/Mac系统

在终端中：

```bash
python3 start_venv.py
```

## 📝 执行流程

脚本将按以下顺序执行：

1. **检查Python版本**
   - 验证Python版本是否 >= 3.8
   - 如果版本过低，脚本将退出并提示升级

2. **检查虚拟环境**
   - 检查venv目录是否存在
   - 验证虚拟环境是否完整

3. **创建虚拟环境**（如果需要）
   - 使用Python内置venv模块创建虚拟环境
   - 虚拟环境目录：`venv/`

4. **检查依赖文件**
   - 验证requirements.txt文件是否存在

5. **安装依赖**
   - 升级pip到最新版本
   - 安装requirements.txt中的所有依赖包
   - 首次运行可能需要几分钟

6. **检查主启动文件**
   - 验证app.py文件是否存在

7. **启动应用**
   - 使用虚拟环境中的Python运行app.py
   - 应用将在默认端口7860启动
## 🔧 手动操作

如果自动脚本遇到问题，可以手动执行以下步骤：

### 1. 创建虚拟环境

```bash
# Windows
python -m venv venv

# Linux/Mac
python3 -m venv venv
```

### 2. 激活虚拟环境

```bash
# Windows (CMD)
venv\Scripts\activate.bat

# Windows (PowerShell)
venv\Scripts\Activate.ps1

# Linux/Mac
source venv/bin/activate
```

### 3. 安装依赖

```bash
pip install -r requirements.txt
```

### 4. 启动应用

```bash
python app.py
```

启动成功后，在浏览器中访问：
```
http://127.0.0.1:7860
```

## 📖 功能特性

### 1. 智能创作 🎯

- **大纲生成**: AI 自动生成完整的小说大纲，支持自定义章节数量
- **章节创作**: 逐章生成，确保情节连贯性和人物一致性
- **断点续写**: 支持暂停和继续，随时保存进度
- **风格定制**: 可调节创意度、语调、人物塑造等参数

### 2. 智能重写 ✍️

- **多格式支持**: 支持 TXT、PDF、EPUB 等格式导入
- **风格模板**: 内置多种写作风格模板（玄幻、都市、悬疑、科幻等）
- **批量处理**: 支持分段重写，保持原文情节
- **实时预览**: 重写过程中实时显示进度和结果

### 3. 多格式导出 📤

| 格式 | 特点 | 适用场景 |
|------|------|----------|
| **Word (.docx)** | 完整格式，支持样式 | 传统出版、编辑修改 |
| **纯文本 (.txt)** | 简洁通用 | 文本处理、二次创作 |
| **Markdown (.md)** | 结构化文本 | 技术文档、版本控制 |
| **HTML (.html)** | 网页格式 | 在线发布、网页展示 |

### 4. 项目管理 📂

- **项目库**: 统一管理所有创作项目
- **元数据存储**: 自动保存项目信息、章节结构、生成时间
- **导出功能**: 从项目库直接导出完整作品
- **版本追踪**: 记录项目创建和更新时间

### 5. 灵活配置 ⚙️

#### API 后端管理
- **多后端支持**: 同时配置多个 AI 服务提供商
- **负载均衡**: 自动轮询可用后端
- **连接测试**: 一键测试后端可用性
- **动态切换**: 运行时切换 API 后端

#### 创作参数调节
```python
# 可调节参数示例
temperature: 0.1-2.0          # 创意度控制
top_p: 0.1-1.0               # 输出多样性
top_k: 1-100                  # 候选词数量
max_tokens: 100-100000        # 生成长度限制
chapter_target_words: 500-10000  # 每章目标字数
```

## 🔧 技术特性

### 1. 错误恢复 🛡️

- **重试机制**: 指数退避算法，自动重试失败的 API 调用
- **异常处理**: 完整的异常捕获和日志记录
- **状态保存**: 生成过程中自动保存进度，支持崩溃恢复

### 2. 缓存机制 💾

- **智能缓存**: 基于内容的缓存键生成，避免重复调用
- **TTL 控制**: 可配置的缓存过期时间
- **磁盘持久化**: 缓存数据持久化到磁盘，重启后仍可用
- **内存管理**: LRU 算法管理内存缓存大小

### 3. 速率限制 ⚡

```python
# 令牌桶算法实现
class RateLimiter:
    def __init__(self, rate=10, window=60):
        self.rate = rate          # 每window秒请求数
        self.window = window      # 时间窗口
        self.tokens = rate        # 当前令牌数
```

- **令牌桶算法**: 平滑的请求速率控制
- **动态调整**: 根据不同后端特性调整速率
- **阻塞模式**: 可选的阻塞等待机制

### 4. 负载均衡 ⚖️

- **轮询算法**: 简单高效的负载分配
- **健康检查**: 自动检测后端可用性
- **故障转移**: 后端故障时自动切换
- **性能监控**: 实时统计各后端响应时间

### 5. 性能监控 📊

```python
# 性能指标示例
performance_metrics = {
    "total_requests": 1250,
    "cache_hit_rate": 0.65,     # 缓存命中率
    "avg_response_time": 2.3,   # 平均响应时间(秒)
    "success_rate": 0.98       # 成功率
}
```

- **实时统计**: 请求次数、响应时间、成功率
- **缓存分析**: 缓存命中率、使用率统计
- **日志记录**: 分级日志系统，便于问题排查

### 6. 线程安全 🔒

```python
# 线程安全设计
class ThreadSafeCache:
    def __init__(self):
        self.lock = threading.Lock()
        self.cache = {}
    
    def get(self, key):
        with self.lock:
            return self.cache.get(key)
```

- **线程锁**: 关键操作使用线程锁保护
- **无状态设计**: 避免共享状态导致的并发问题
- **原子操作**: 确保数据一致性

## ⚙️ 配置说明

### 环境变量配置

```bash
# Web 服务器配置
export NOVEL_TOOL_HOST=127.0.0.1      # 监听地址
export NOVEL_TOOL_PORT=7860            # 监听端口
export NOVEL_TOOL_SHOW_ERRORS=false     # 显示错误信息
export NOVEL_TOOL_CONCURRENCY=4        # 并发线程数
export NOVEL_TOOL_QUEUE_MAX=50         # 队列最大长度
```

### 配置文件结构

```json
{
    "version": "2.0.0",
    "backends": [
        {
            "name": "阿里云",
            "type": "openai",
            "base_url": "https://open.bigmodel.cn/api/paas",
            "api_key": "your-api-key",
            "model": "glm-4.7",
            "enabled": true,
            "timeout": 30,
            "retry_times": 3
        }
    ],
    "generation": {
        "temperature": 0.8,
        "top_p": 0.9,
        "top_k": 40,
        "max_tokens": 200000,
        "chapter_target_words": 2500,
        "writing_style": "流畅自然，情节紧凑，人物刻画细腻",
        "writing_tone": "中性",
        "character_development": "详细",
        "plot_complexity": "复杂"
    }
}
```

### 支持的 API 后端

| 后端类型 | 示例配置 | 特点 |
|----------|----------|------|
| **OpenAI** | `base_url: https://api.openai.com/v1` | GPT-4、GPT-3.5 |
| **Claude** | `base_url: https://api.anthropic.com` | Claude 3 系列 |
| **Ollama** | `base_url: http://localhost:11434/v1` | 本地模型部署 |
| **自定义** | `base_url: https://your-api.com` | 兼容 OpenAI 协议 |

## 📁 项目结构

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
├── 📄 requirements.txt          # Python 依赖列表
├── 📄 LICENSE                  # MIT 许可证
├── 📄 README.md                # 项目文档
├── 📁 config/                  # 配置文件目录
│   ├── 📄 novel_tool_config.json  # 主配置文件
│   └── 📄 backups/              # 配置备份目录
├── 📁 projects/                 # 项目存储目录
├── 📁 exports/                 # 导出文件目录
├── 📁 logs/                     # 日志文件目录
├── 📁 cache/                    # 缓存文件目录
└── 📄 .env.template            # 环境变量模板
```

## 🛠️ 开发指南

### 添加新的写作风格

在 `novel_generator.py` 中的 `PRESET_TEMPLATES` 字典添加新风格：

```python
PRESET_TEMPLATES = {
    # ... 现有风格 ...
    "重写风格 - 新风格": "新风格的描述和要求...",
}
```

### 扩展导出格式

在 `exporter.py` 中添加新的导出函数：

```python
def export_to_new_format(content: str, title: str) -> tuple[bool, str]:
    """新的导出格式"""
    try:
        # 实现导出逻辑
        return True, "导出成功"
    except Exception as e:
        return False, f"导出失败: {str(e)}"
```

### 自定义 API 后端

1. 在配置文件中添加新的后端配置
2. 确保支持 OpenAI 兼容的 API 接口
3. 测试连接和基本功能

## 🐛 故障排除

### 常见问题

**Q: 启动时提示缺少依赖包**
```bash
# 重新运行快速初始化
python quickstart.py
# 或手动安装
pip install -r requirements.txt
```

**Q: API 调用失败**
- 检查网络连接
- 验证 API 密钥是否正确
- 确认后端服务是否正常运行
- 查看 `logs/` 目录下的详细日志

**Q: 导出文件失败**
- 确保有足够的磁盘空间
- 检查文件权限
- 尝试更换导出格式

### 日志文件位置

```
logs/
├── novel_tool_ui.log          # 主应用程序日志
├── novel_tool_api.log         # API 调用日志
├── novel_tool_errors.log     # 错误日志
└── performance.log           # 性能监控日志
```

## 📊 性能优化建议

### 1. 缓存优化
- 启用响应缓存减少 API 调用
- 合理设置缓存 TTL 时间
- 定期清理过期缓存

### 2. 并发控制
- 根据硬件性能调整并发线程数
- 避免过多并发请求导致 API 限流
- 使用队列机制平滑请求

### 3. 内存管理
- 监控内存使用情况
- 及时清理不再需要的数据
- 使用流式处理减少内存占用

## 🤝 贡献指南

我们欢迎社区贡献！请遵循以下步骤：

1. **Fork 项目**
2. **创建功能分支** (`git checkout -b feature/AmazingFeature`)
3. **提交更改** (`git commit -m 'Add some AmazingFeature'`)
4. **推送分支** (`git push origin feature/AmazingFeature`)
5. **创建 Pull Request**

### 开发环境设置

```bash
# 克隆项目
git clone <repository-url>
cd ai小说生成工具正式版V3.0

# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Linux/Mac
# 或 venv\Scripts\activate  # Windows

# 安装开发依赖
pip install -r requirements.txt
pip install pytest black flake8
```

### 代码规范

- 使用 Black 进行代码格式化
- 遵循 PEP 8 编码规范
- 添加适当的注释和文档字符串
- 编写单元测试覆盖新功能

## 📞 联系方式

- **项目主页**: https://github.com/yangqi1309134997-coder/ai-novel-generator/
- **问题反馈**: 1309134997@qq.com
- **功能建议**: 1309134997@qq.com
- **技术支持**: https://www.bilibili.com/video/BV1yarvBkEi6/?share_source=copy_web&vd_source=d7e56ff6a5e643c81fb73e628755d061
- **官方网站**: https://hcnote.cn/


### 开发团队

- **幻城** - 项目架构设计与核心开发
- **新疆幻城网安科技有限责任公司** - 技术支持与维护

## 📄 许可证

本项目采用 [MIT License](LICENSE) 许可证。

```
MIT License

Copyright (c) 2026 新疆幻城网安科技有限责任公司 (幻城科技)

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

---

## 🎉 致谢

感谢所有为这个项目做出贡献的开发者和用户！

如果您觉得这个项目对您有帮助，请考虑给我们一个 ⭐ Star！


**开始您的 AI 创作之旅吧！** 🚀✨


