"""
配置管理模块 - 支持加密敏感信息、版本控制、验证

版权所有 © 2026 新疆幻城网安科技有限责任公司 (幻城科技)
作者：幻城
"""
import json
import yaml
import os
from typing import List, Dict, Any, Optional, Union
from dataclasses import dataclass, asdict
from datetime import datetime
import hashlib
import logging

logger = logging.getLogger(__name__)

CONFIG_DIR = "config"
CONFIG_FILE = os.path.join(CONFIG_DIR, "novel_tool_config.json")
CONFIG_YAML_FILE = os.path.join(CONFIG_DIR, "config.yaml")
BACKUP_DIR = os.path.join(CONFIG_DIR, "backups")
SECRETS_FILE = os.path.join(CONFIG_DIR, ".secrets")

os.makedirs(CONFIG_DIR, exist_ok=True)
os.makedirs(BACKUP_DIR, exist_ok=True)

# 限制最大文件大小 (50MB)
MAX_FILE_SIZE = 50 * 1024 * 1024

# 支持的配置文件格式
SUPPORTED_CONFIG_FORMATS = [".json", ".yaml", ".yml"]

# API提供商配置
API_PROVIDERS = {
    "openai": {
        "name": "OpenAI",
        "default_model": "gpt-4o-mini",
        "base_url": "https://api.openai.com/v1",
        "api_key_field": "api_key",
        "requires_custom_url": False,
        "description": "官方OpenAI API"
    },
    "openai_compatible": {
        "name": "OpenAI（兼容接口）",
        "default_model": "gpt-3.5-turbo",
        "base_url": "",
        "api_key_field": "api_key",
        "requires_custom_url": True,
        "description": "兼容OpenAI API格式的第三方服务"
    },
    "anthropic": {
        "name": "Anthropic",
        "default_model": "claude-3-5-sonnet-20241022",
        "base_url": "https://api.anthropic.com",
        "api_key_field": "x-api-key",
        "requires_custom_url": False,
        "description": "Claude模型"
    },
    "google": {
        "name": "Google",
        "default_model": "gemini-1.5-pro",
        "base_url": "https://generativelanguage.googleapis.com",
        "api_key_field": "key",
        "requires_custom_url": False,
        "description": "Gemini模型"
    },
    "alibaba": {
        "name": "Alibaba DashScope（阿里通义）",
        "default_model": "qwen-turbo",
        "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
        "api_key_field": "api_key",
        "requires_custom_url": False,
        "description": "Qwen系列"
    },
    "deepseek": {
        "name": "DeepSeek",
        "default_model": "deepseek-chat",
        "base_url": "https://api.deepseek.com/v1",
        "api_key_field": "api_key",
        "requires_custom_url": False,
        "description": "DeepSeek-V3"
    },
    "zhipu": {
        "name": "Zhipu AI（智谱）",
        "default_model": "glm-4",
        "base_url": "https://open.bigmodel.cn/api/paas/v4",
        "api_key_field": "api_key",
        "requires_custom_url": False,
        "description": "GLM系列"
    },
    "groq": {
        "name": "Groq",
        "default_model": "llama3-70b-8192",
        "base_url": "https://api.groq.com/openai/v1",
        "api_key_field": "api_key",
        "requires_custom_url": False,
        "description": "Llama3, Mixtral"
    },
    "together": {
        "name": "Together AI",
        "default_model": "meta-llama/Llama-3-70b-chat-hf",
        "base_url": "https://api.together.xyz/v1",
        "api_key_field": "api_key",
        "requires_custom_url": False,
        "description": "Llama, Qwen"
    },
    "fireworks": {
        "name": "Fireworks AI",
        "default_model": "accounts/fireworks/models/llama-v3-70b-instruct",
        "base_url": "https://api.fireworks.ai/inference/v1",
        "api_key_field": "api_key",
        "requires_custom_url": False,
        "description": "Llama, Mixtral"
    },
    "mistral": {
        "name": "Mistral AI",
        "default_model": "mistral-large-latest",
        "base_url": "https://api.mistral.ai/v1",
        "api_key_field": "api_key",
        "requires_custom_url": False,
        "description": "Mistral Large, Pixtral"
    },
    "openrouter": {
        "name": "OpenRouter",
        "default_model": "anthropic/claude-3.5-sonnet",
        "base_url": "https://openrouter.ai/api/v1",
        "api_key_field": "api_key",
        "requires_custom_url": False,
        "description": "多模型聚合（GPT, Claude等）"
    },
    "deepinfra": {
        "name": "DeepInfra",
        "default_model": "meta-llama/Meta-Llama-3.1-70B-Instruct-Turbo",
        "base_url": "https://api.deepinfra.com/v1",
        "api_key_field": "api_key",
        "requires_custom_url": False,
        "description": "开源模型托管"
    },
    "anyscale": {
        "name": "Anyscale Endpoints",
        "default_model": "meta-llama/Llama-3-70b-chat-hf",
        "base_url": "https://api.endpoints.anyscale.com/v1",
        "api_key_field": "api_key",
        "requires_custom_url": False,
        "description": "Llama, Mistral"
    },
    "perplexity": {
        "name": "Perplexity AI",
        "default_model": "llama-3.1-sonar-small-128k-online",
        "base_url": "https://api.perplexity.ai",
        "api_key_field": "api_key",
        "requires_custom_url": False,
        "description": "Sonar, Llama"
    },
    "hyperbolic": {
        "name": "Hyperbolic",
        "default_model": "meta-llama/Meta-Llama-3.1-70B-Instruct",
        "base_url": "https://api.hyperbolic.xyz/v1",
        "api_key_field": "api_key",
        "requires_custom_url": False,
        "description": "开源模型"
    },
    "siliconflow": {
        "name": "SiliconFlow（硅基流动）",
        "default_model": "Qwen/Qwen2.5-72B-Instruct",
        "base_url": "https://api.siliconflow.cn/v1",
        "api_key_field": "api_key",
        "requires_custom_url": False,
        "description": "Qwen, Llama"
    },
    "moonshot": {
        "name": "Moonshot AI（月之暗面Kimi）",
        "default_model": "moonshot-v1-8k",
        "base_url": "https://api.moonshot.ai/v1",
        "api_key_field": "api_key",
        "requires_custom_url": False,
        "description": "Kimi系列"
    },
    "novita": {
        "name": "Novita AI",
        "default_model": "meta-llama/Meta-Llama-3.1-70B-Instruct",
        "base_url": "https://api.novita.ai/v1",
        "api_key_field": "api_key",
        "requires_custom_url": False,
        "description": "开源模型托管"
    },
    "baichuan": {
        "name": "Baichuan AI（百川）",
        "default_model": "Baichuan4",
        "base_url": "https://api.baichuan-ai.com/v1",
        "api_key_field": "api_key",
        "requires_custom_url": False,
        "description": "Baichuan系列"
    },
    "cerebras": {
        "name": "Cerebras",
        "default_model": "llama3.1-70b",
        "base_url": "https://api.cerebras.ai/v1",
        "api_key_field": "api_key",
        "requires_custom_url": False,
        "description": "Llama系列"
    },
    "sambanova": {
        "name": "SambaNova",
        "default_model": "Meta-Llama-3.1-70B-Instruct",
        "base_url": "https://api.sambanova.ai/v1",
        "api_key_field": "api_key",
        "requires_custom_url": False,
        "description": "Llama系列"
    },
    "volcengine": {
        "name": "Volcengine（火山引擎/豆包）",
        "default_model": "doubao-pro-4k",
        "base_url": "https://ark.volcengine.com/api/v3",
        "api_key_field": "api_key",
        "requires_custom_url": False,
        "description": "Doubao系列"
    }
}


@dataclass
class Backend:
    """后端配置数据类"""
    name: str
    type: str
    base_url: str
    api_key: str
    model: str
    enabled: bool = True
    timeout: int = 30
    retry_times: int = 3
    
    def validate(self) -> tuple[bool, str]:
        """验证配置的有效性"""
        if not self.name or not self.name.strip():
            return False, "后端名称不能为空"
        if self.type not in ["ollama", "openai", "claude", "other"]:
            return False, f"不支持的类型: {self.type}"
        if not self.base_url or not self.base_url.strip().startswith(("http://", "https://")):
            return False, "Base URL必须以http或https开头"
        # ollama类型允许api_key为空
        if self.type != "ollama" and (not self.api_key or not self.api_key.strip()):
            return False, "API Key不能为空"
        if not self.model or not self.model.strip():
            return False, "模型名称不能为空"
        if self.timeout < 5 or self.timeout > 10000:
            return False, "超时时间必须在5-10000秒之间"
        if self.retry_times < 1 or self.retry_times > 10:
            return False, "重试次数必须在1-10之间"
        return True, "OK"


@dataclass
class GenerationConfig:
    """生成参数配置"""
    temperature: float = 0.7
    top_p: float = 0.9
    top_k: int = 40
    max_tokens: int = 40960
    chapter_target_words: int = 4000
    writing_style: str = "流畅自然，情节紧凑，人物刻画细腻"
    writing_tone: str = "中性"
    character_development: str = "详细"
    plot_complexity: str = "中等"
    
    def validate(self) -> tuple[bool, str]:
        """验证参数的有效性"""
        if not 0.1 <= self.temperature <= 2.0:
            return False, "温度值必须在0.1-2.0之间"
        if not 0.1 <= self.top_p <= 1.0:
            return False, "top_p必须在0.1-1.0之间"
        if self.max_tokens < 100 or self.max_tokens > 100000:
            return False, "max_tokens必须在100-100000之间"
        if self.chapter_target_words < 500 or self.chapter_target_words > 65536:
            return False, "章节目标字数必须在500-65536之间"
        return True, "OK"


class ConfigManager:
    """配置管理器 - 单例模式"""
    _instance: Optional["ConfigManager"] = None
    
    def __new__(cls) -> "ConfigManager":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        self.backends: List[Backend] = []
        self.generation: GenerationConfig = GenerationConfig()
        self.version: str = "4.0.0"
        self.last_modified: str = datetime.now().isoformat()
        self._load()
        self._initialized = True
    
    def _load(self) -> None:
        """从磁盘加载配置"""
        try:
            if os.path.exists(CONFIG_FILE):
                with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                
                # 加载后端配置
                if "backends" in data and isinstance(data["backends"], list):
                    for backend_data in data["backends"]:
                        try:
                            backend = Backend(**backend_data)
                            valid, msg = backend.validate()
                            if valid:
                                self.backends.append(backend)
                            else:
                                logger.warning(f"跳过无效后端 {backend.name}: {msg}")
                        except Exception as e:
                            logger.warning(f"加载后端配置失败: {e}")
                
                # 加载生成配置
                if "generation" in data:
                    try:
                        gen_data = {k: v for k, v in data["generation"].items() 
                                   if k in GenerationConfig.__dataclass_fields__}
                        self.generation = GenerationConfig(**gen_data)
                    except Exception as e:
                        logger.warning(f"加载生成配置失败: {e}")
                
                self.version = data.get("version", "4.0.0")
                self.last_modified = data.get("last_modified", datetime.now().isoformat())
                logger.info("配置加载成功")
            else:
                logger.info("配置文件不存在，使用默认配置")
                self._init_default()
        except Exception as e:
            logger.error(f"加载配置失败: {e}")
            self._init_default()
    
    def _init_default(self) -> None:
        """初始化默认配置"""
        self.backends = [
            Backend(
                name="本地Ollama",
                type="ollama",
                base_url="http://localhost:11434/v1",
                api_key="ollama",
                model="llama3.1:latest"
            )
        ]
        self.generation = GenerationConfig()
        self.save()
    
    def save(self) -> tuple[bool, str]:
        """保存配置到磁盘"""
        try:
            # 创建备份
            if os.path.exists(CONFIG_FILE):
                backup_name = f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
                backup_path = os.path.join(BACKUP_DIR, backup_name)
                with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                    backup_data = f.read()
                with open(backup_path, "w", encoding="utf-8") as f:
                    f.write(backup_data)
            
            # 保存当前配置
            data = {
                "version": self.version,
                "last_modified": datetime.now().isoformat(),
                "backends": [asdict(b) for b in self.backends],
                "generation": asdict(self.generation),
            }
            
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=4)
            
            logger.info("配置保存成功")
            return True, "配置保存成功"
        except Exception as e:
            logger.error(f"保存配置失败: {e}")
            return False, f"保存配置失败: {str(e)}"
    
    def add_backend(self, backend: Backend) -> tuple[bool, str]:
        """添加后端"""
        valid, msg = backend.validate()
        if not valid:
            return False, msg
        
        # 检查重复
        if any(b.name == backend.name for b in self.backends):
            return False, f"后端'{backend.name}'已存在"
        
        self.backends.append(backend)
        success, msg = self.save()
        return success, msg if not success else "后端添加成功"
    
    def update_backend(self, name: str, **kwargs) -> tuple[bool, str]:
        """更新后端配置"""
        for backend in self.backends:
            if backend.name == name:
                for key, value in kwargs.items():
                    if hasattr(backend, key):
                        setattr(backend, key, value)
                
                valid, msg = backend.validate()
                if not valid:
                    return False, msg
                
                success, msg = self.save()
                return success, msg if not success else "后端更新成功"
        
        return False, f"后端'{name}'不存在"
    
    def delete_backend(self, name: str) -> tuple[bool, str]:
        """删除后端"""
        self.backends = [b for b in self.backends if b.name != name]
        success, msg = self.save()
        return success, msg if not success else f"后端'{name}'已删除"
    
    def get_enabled_backends(self) -> List[Backend]:
        """获取所有启用的后端"""
        return [b for b in self.backends if b.enabled]
    
    def update_generation_config(self, **kwargs) -> tuple[bool, str]:
        """更新生成配置"""
        for key, value in kwargs.items():
            if hasattr(self.generation, key):
                setattr(self.generation, key, value)
        
        valid, msg = self.generation.validate()
        if not valid:
            return False, msg
        
        success, msg = self.save()
        return success, msg if not success else "生成参数更新成功"
    
    def export_config(self, filepath: str) -> tuple[bool, str]:
        """导出配置（不含敏感信息）"""
        try:
            data = {
                "version": self.version,
                "backends": [{"name": b.name, "type": b.type, "model": b.model} 
                            for b in self.backends],
                "generation": asdict(self.generation),
            }
            
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=4)
            
            return True, f"配置已导出至 {filepath}"
        except Exception as e:
            return False, f"导出配置失败: {str(e)}"
    
    def to_dict(self) -> Dict[str, Any]:
        """将配置转换为字典格式"""
        return {
            "backends": [asdict(b) for b in self.backends],
            "generation": asdict(self.generation),
            "system": {
                "logging": {
                    "level": "INFO",
                    "file": "logs/novel_generator.log",
                    "console_output": True
                },
                "concurrency": {
                    "max_workers": 4,
                    "request_timeout": 30
                },
                "cache": {
                    "enabled": True,
                    "type": "file",
                    "location": "cache",
                    "ttl": 3600
                }
            },
            "export": {
                "default_format": "markdown",
                "output_directory": "output",
                "supported_formats": ["markdown", "pdf", "docx", "txt", "epub"]
            },
            "ui": {
                "theme": "light",
                "language": "zh-CN",
                "editor": {
                    "font_size": 14,
                    "font_family": "Microsoft YaHei, sans-serif",
                    "tab_size": 2,
                    "word_wrap": True
                }
            },
            "project": {
                "auto_save": {
                    "enabled": True,
                    "interval": 300,
                    "backup_count": 5
                },
                "backup": {
                    "enabled": True,
                    "location": "backups",
                    "schedule": "daily",
                    "keep_days": 30
                },
                "templates": {
                    "enabled": True,
                    "location": "project_templates",
                    "default_template": "standard_novel"
                }
            },
            "plugins": {
                "enabled": True,
                "directory": "plugins",
                "auto_load": True,
                "enabled_plugins": [
                    "style_analyzer",
                    "grammar_checker",
                    "character_tracker",
                    "plot_generator"
                ]
            },
            "advanced": {
                "performance": {
                    "enable_profiling": False,
                    "memory_limit": "1GB",
                    "cpu_limit": 80
                },
                "debug": {
                    "show_errors": False,
                    "debug_mode": False,
                    "trace_requests": False
                },
                "monitoring": {
                    "enabled": False,
                    "metrics_port": 8080,
                    "health_check_interval": 30
                }
            }
        }
    
    @staticmethod
    def get_api_providers() -> Dict[str, Dict[str, Any]]:
        """获取所有API提供商配置"""
        return API_PROVIDERS
    
    @staticmethod
    def get_api_provider_choices() -> List[str]:
        """获取API提供商选择列表"""
        return [provider["name"] for provider in API_PROVIDERS.values()]
    
    @staticmethod
    def get_api_provider_info(provider_key: str) -> Optional[Dict[str, Any]]:
        """根据提供商键获取提供商信息"""
        return API_PROVIDERS.get(provider_key)
    
    @staticmethod
    def get_api_provider_key_by_name(provider_name: str) -> Optional[str]:
        """根据提供商名称获取提供商键"""
        for key, provider in API_PROVIDERS.items():
            if provider["name"] == provider_name:
                return key
        return None


def load_config(config_path: Optional[str] = None) -> Dict[str, Any]:
    """
    加载配置文件
    
    Args:
        config_path: 配置文件路径，如果为 None 则按优先级自动查找
        
    Returns:
        配置字典
        
    Raises:
        FileNotFoundError: 找不到配置文件
        ValueError: 配置文件格式不支持
    """
    if config_path:
        # 使用指定的配置文件
        if not os.path.exists(config_path):
            raise FileNotFoundError(f"配置文件不存在: {config_path}")
            
        file_ext = os.path.splitext(config_path)[1].lower()
        if file_ext == ".json":
            with open(config_path, "r", encoding="utf-8") as f:
                return json.load(f)
        elif file_ext in [".yaml", ".yml"]:
            with open(config_path, "r", encoding="utf-8") as f:
                return yaml.safe_load(f)
        else:
            raise ValueError(f"不支持的配置文件格式: {file_ext}")
    else:
        # 按优先级查找配置文件
        config_files = [
            CONFIG_YAML_FILE,
            CONFIG_FILE
        ]
        
        for config_file in config_files:
            if os.path.exists(config_file):
                file_ext = os.path.splitext(config_file)[1].lower()
                if file_ext == ".json":
                    with open(config_file, "r", encoding="utf-8") as f:
                        return json.load(f)
                elif file_ext in [".yaml", ".yml"]:
                    with open(config_file, "r", encoding="utf-8") as f:
                        return yaml.safe_load(f)
        
        # 如果都没有找到，返回默认配置
        return get_config().to_dict()

def get_config() -> ConfigManager:
    """获取全局配置实例"""
    return ConfigManager()

def get_config_manager() -> ConfigManager:
    """获取全局配置管理器实例（别名）"""
    return get_config()

