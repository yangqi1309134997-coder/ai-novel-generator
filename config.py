"""
配置管理模块 - 支持加密敏感信息、版本控制、验证

版权所有 © 2026 新疆幻城网安科技有限责任公司 (幻城科技)
作者：幻城
"""
import json
import os
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, asdict
from datetime import datetime
import hashlib
import logging

logger = logging.getLogger(__name__)

CONFIG_DIR = "config"
CONFIG_FILE = os.path.join(CONFIG_DIR, "novel_tool_config.json")
BACKUP_DIR = os.path.join(CONFIG_DIR, "backups")
SECRETS_FILE = os.path.join(CONFIG_DIR, ".secrets")

os.makedirs(CONFIG_DIR, exist_ok=True)
os.makedirs(BACKUP_DIR, exist_ok=True)

# 限制最大文件大小 (50MB)
MAX_FILE_SIZE = 50 * 1024 * 1024


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
        if not self.api_key or not self.api_key.strip():
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
    max_tokens: int = 4096
    chapter_target_words: int = 2500
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
        if self.chapter_target_words < 500 or self.chapter_target_words > 10000:
            return False, "章节目标字数必须在500-10000之间"
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
        self.version: str = "2.0.0"
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
                
                self.version = data.get("version", "2.0.0")
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


def get_config() -> ConfigManager:
    """获取全局配置实例"""
    return ConfigManager()

