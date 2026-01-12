"""
Web API 接口配置管理模块
支持通过Web UI添加、编辑、删除、测试API接口

版权所有 © 2026 新疆幻城网安科技有限责任公司 (幻城科技)
作者：幻城
"""
import json
from typing import Dict, List, Tuple, Any
from dataclasses import asdict
from config import Backend, get_config
from api_client import get_api_client, reinit_api_client
from logger import get_logger

logger = get_logger("ConfigAPI")


class ConfigAPIManager:
    """配置管理API"""
    
    @staticmethod
    def list_backends() -> Dict[str, Any]:
        """获取所有后端列表"""
        try:
            config = get_config()
            backends_data = []
            for backend in config.backends:
                backend_dict = asdict(backend)
                backends_data.append(backend_dict)
            return {
                "success": True,
                "data": backends_data,
                "message": f"已加载 {len(backends_data)} 个后端"
            }
        except Exception as e:
            logger.error(f"获取后端列表失败: {e}")
            return {
                "success": False,
                "data": [],
                "message": f"获取后端列表失败: {str(e)}"
            }
    
    @staticmethod
    def add_backend(name: str, type: str, base_url: str, api_key: str, 
                    model: str, timeout: int = 30, retry_times: int = 3,
                    enabled: bool = True) -> Dict[str, Any]:
        """添加新的后端配置"""
        try:
            config = get_config()
            
            # 检查名称是否重复
            for backend in config.backends:
                if backend.name == name:
                    return {
                        "success": False,
                        "message": f"后端名称 '{name}' 已存在，请使用不同的名称"
                    }
            
            # 创建新的后端
            new_backend = Backend(
                name=name,
                type=type,
                base_url=base_url,
                api_key=api_key,
                model=model,
                timeout=timeout,
                retry_times=retry_times,
                enabled=enabled
            )
            
            # 验证后端配置
            valid, msg = new_backend.validate()
            if not valid:
                return {
                    "success": False,
                    "message": f"配置验证失败: {msg}"
                }
            
            # 添加后端
            config.backends.append(new_backend)
            success, save_msg = config.save()
            
            if success:
                logger.info(f"成功添加后端: {name}")
                return {
                    "success": True,
                    "message": f"后端 '{name}' 添加成功",
                    "backend": asdict(new_backend)
                }
            else:
                return {
                    "success": False,
                    "message": f"保存配置失败: {save_msg}"
                }
                
        except Exception as e:
            logger.error(f"添加后端失败: {e}")
            return {
                "success": False,
                "message": f"添加后端失败: {str(e)}"
            }
    
    @staticmethod
    def update_backend(name: str, **kwargs) -> Dict[str, Any]:
        """更新后端配置"""
        try:
            config = get_config()
            success, msg = config.update_backend(name, **kwargs)
            
            if success:
                logger.info(f"成功更新后端: {name}")
                return {
                    "success": True,
                    "message": msg
                }
            else:
                return {
                    "success": False,
                    "message": msg
                }
                
        except Exception as e:
            logger.error(f"更新后端失败: {e}")
            return {
                "success": False,
                "message": f"更新后端失败: {str(e)}"
            }
    
    @staticmethod
    def delete_backend(name: str) -> Dict[str, Any]:
        """删除后端配置"""
        try:
            config = get_config()
            success, msg = config.delete_backend(name)
            
            if success:
                logger.info(f"成功删除后端: {name}")
                return {
                    "success": True,
                    "message": msg
                }
            else:
                return {
                    "success": False,
                    "message": msg
                }
                
        except Exception as e:
            logger.error(f"删除后端失败: {e}")
            return {
                "success": False,
                "message": f"删除后端失败: {str(e)}"
            }
    
    @staticmethod
    def toggle_backend(name: str, enabled: bool) -> Dict[str, Any]:
        """启用/禁用后端"""
        try:
            config = get_config()
            success, msg = config.update_backend(name, enabled=enabled)
            
            if success:
                status = "启用" if enabled else "禁用"
                logger.info(f"已{status}后端: {name}")
                return {
                    "success": True,
                    "message": f"后端已{status}"
                }
            else:
                return {
                    "success": False,
                    "message": msg
                }
                
        except Exception as e:
            logger.error(f"切换后端状态失败: {e}")
            return {
                "success": False,
                "message": f"切换后端状态失败: {str(e)}"
            }
    
    @staticmethod
    def test_backend(name: str) -> Dict[str, Any]:
        """测试后端连接"""
        try:
            config = get_config()
            backend = None
            
            # 查找指定的后端
            for b in config.backends:
                if b.name == name:
                    backend = b
                    break
            
            if not backend:
                return {
                    "success": False,
                    "message": f"后端 '{name}' 不存在"
                }
            
            # 测试连接
            if not backend.enabled:
                return {
                    "success": False,
                    "message": f"后端 '{name}' 已被禁用，无法测试"
                }
            
            # 使用API客户端测试
            try:
                api_client = get_api_client()
                # 尝试获取模型信息来测试连接
                test_response = api_client.test_connection(backend.base_url, backend.api_key)
                
                if test_response:
                    logger.info(f"后端连接测试成功: {name}")
                    return {
                        "success": True,
                        "message": f"后端 '{name}' 连接成功",
                        "backend": name,
                        "model": backend.model
                    }
                else:
                    return {
                        "success": False,
                        "message": f"后端 '{name}' 连接失败：无法获取响应"
                    }
            except Exception as test_error:
                logger.error(f"后端连接测试异常: {test_error}")
                return {
                    "success": False,
                    "message": f"后端 '{name}' 连接失败: {str(test_error)}"
                }
                
        except Exception as e:
            logger.error(f"测试后端失败: {e}")
            return {
                "success": False,
                "message": f"测试后端失败: {str(e)}"
            }
    
    @staticmethod
    def get_backend_types() -> List[str]:
        """获取支持的后端类型列表"""
        return ["ollama", "openai", "claude", "other"]
    
    @staticmethod
    def export_config(filepath: str) -> Dict[str, Any]:
        """导出配置文件"""
        try:
            config = get_config()
            success, msg = config.export_config(filepath)
            
            if success:
                return {
                    "success": True,
                    "message": msg
                }
            else:
                return {
                    "success": False,
                    "message": msg
                }
                
        except Exception as e:
            logger.error(f"导出配置失败: {e}")
            return {
                "success": False,
                "message": f"导出配置失败: {str(e)}"
            }


# 全局API管理器实例
config_api = ConfigAPIManager()
