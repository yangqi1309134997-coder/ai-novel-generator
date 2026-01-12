"""
API调用模块 - 支持重试、速率限制、缓存、负载均衡

版权所有 © 2026 新疆幻城网安科技有限责任公司 (幻城科技)
作者：幻城
"""
import time
import hashlib
import json
import os
import threading
from typing import List, Dict, Any, Optional, Callable
from dataclasses import dataclass
from datetime import datetime, timedelta
from functools import wraps
import logging
from openai import OpenAI, RateLimitError, APIError
import pickle

from config import get_config, Backend

logger = logging.getLogger(__name__)

MODULE_ROOT = os.path.dirname(os.path.abspath(__file__))
CACHE_DIR = os.path.join(MODULE_ROOT, "cache")
os.makedirs(CACHE_DIR, exist_ok=True)

# 最大缓存条数
MAX_CACHE_SIZE = 1000


@dataclass
class CacheEntry:
    """缓存条目"""
    key: str
    value: str
    timestamp: datetime
    ttl: int = 3600  # 默认1小时过期


class ResponseCache:
    """响应缓存管理器"""
    
    def __init__(self, max_size: int = MAX_CACHE_SIZE):
        self.cache: Dict[str, CacheEntry] = {}
        self.max_size = max_size
        self.lock = threading.Lock()
        self._load_from_disk()
    
    def _generate_key(self, messages: List[Dict], model: str) -> str:
        """生成缓存key"""
        content = json.dumps(messages, sort_keys=True, ensure_ascii=False) + model
        return hashlib.md5(content.encode('utf-8')).hexdigest()
    
    def get(self, messages: List[Dict], model: str) -> Optional[str]:
        """获取缓存"""
        key = self._generate_key(messages, model)
        
        with self.lock:
            if key in self.cache:
                entry = self.cache[key]
                # 检查是否过期
                if datetime.now() - entry.timestamp < timedelta(seconds=entry.ttl):
                    logger.debug(f"缓存命中: {key}")
                    return entry.value
                else:
                    del self.cache[key]
        
        return None
    
    def set(self, messages: List[Dict], model: str, value: str, ttl: int = 3600) -> None:
        """设置缓存"""
        key = self._generate_key(messages, model)
        
        with self.lock:
            # 当缓存满时，删除最老的条目
            if len(self.cache) >= self.max_size:
                oldest_key = min(self.cache.keys(),
                               key=lambda k: self.cache[k].timestamp)
                del self.cache[oldest_key]
            
            self.cache[key] = CacheEntry(
                key=key,
                value=value,
                timestamp=datetime.now(),
                ttl=ttl
            )
            logger.debug(f"缓存设置: {key}")
            # 尝试保存到磁盘（容错）
            try:
                self._save_to_disk()
            except Exception:
                logger.debug("缓存保存到磁盘时发生错误（已忽略）")
    
    def clear(self) -> None:
        """清空缓存"""
        with self.lock:
            self.cache.clear()
        logger.info("缓存已清空")
    
    def _save_to_disk(self) -> None:
        """保存缓存到磁盘"""
        try:
            cache_file = os.path.join(CACHE_DIR, "response_cache.json")
            serializable: Dict[str, Dict[str, Any]] = {}
            for k, v in self.cache.items():
                serializable[k] = {
                    "value": v.value,
                    "timestamp": v.timestamp.isoformat(),
                    "ttl": v.ttl,
                }
            with open(cache_file, "w", encoding="utf-8") as f:
                json.dump(serializable, f, ensure_ascii=False)
        except Exception as e:
            logger.warning(f"保存缓存到磁盘失败: {e}")
    
    def _load_from_disk(self) -> None:
        """从磁盘加载缓存"""
        try:
            cache_file = os.path.join(CACHE_DIR, "response_cache.json")
            if os.path.exists(cache_file):
                with open(cache_file, "r", encoding="utf-8") as f:
                    raw = json.load(f)
                loaded: Dict[str, CacheEntry] = {}
                for k, v in raw.items():
                    try:
                        ts = datetime.fromisoformat(v.get("timestamp"))
                    except Exception:
                        ts = datetime.now()
                    loaded[k] = CacheEntry(key=k, value=v.get("value", ""), timestamp=ts, ttl=int(v.get("ttl", 3600)))
                self.cache = loaded
                logger.info(f"从磁盘加载 {len(self.cache)} 条缓存")
        except Exception as e:
            logger.warning(f"从磁盘加载缓存失败: {e}")


class RateLimiter:
    """速率限制器 - 令牌桶算法"""
    
    def __init__(self, rate: float = 10, window: int = 60):
        """
        Args:
            rate: 每window秒的请求数
            window: 时间窗口（秒）
        """
        self.rate = rate
        self.window = window
        self.tokens = rate
        self.last_update = time.time()
        self.lock = threading.Lock()
    
    def acquire(self, tokens: int = 1, blocking: bool = True) -> bool:
        """获取令牌"""
        with self.lock:
            now = time.time()
            elapsed = now - self.last_update
            
            # 补充令牌
            self.tokens = min(self.rate, self.tokens + elapsed * self.rate / self.window)
            self.last_update = now
            
            if self.tokens >= tokens:
                self.tokens -= tokens
                return True
            
            if blocking:
                wait_time = (tokens - self.tokens) * self.window / self.rate
                time.sleep(wait_time)
                self.tokens = 0
                return True
            
            return False


class APIClient:
    """API客户端 - 支持重试、速率限制、缓存、负载均衡"""
    
    def __init__(self):
        self.config = get_config()
        self.cache = ResponseCache()
        self.clients: List[tuple[Backend, OpenAI]] = []
        self.rate_limiters: Dict[str, RateLimiter] = {}
        self.current_client_index = 0
        self.lock = threading.Lock()
        self._init_clients()
    
    def _init_clients(self) -> None:
        """初始化所有客户端"""
        self.clients = []
        enabled_backends = self.config.get_enabled_backends()
        
        if not enabled_backends:
            logger.error("没有启用的后端")
            return
        
        for backend in enabled_backends:
            try:
                client = OpenAI(
                    base_url=backend.base_url.rstrip("/"),
                    api_key=backend.api_key,
                    timeout=backend.timeout
                )
                self.clients.append((backend, client))
                
                # 为每个后端创建速率限制器
                limiter_key = f"{backend.name}_{backend.model}"
                if limiter_key not in self.rate_limiters:
                    # 假设每个后端最多10个并发请求/分钟
                    self.rate_limiters[limiter_key] = RateLimiter(rate=10, window=60)
                
                logger.info(f"后端初始化成功: {backend.name}")
            except Exception as e:
                logger.error(f"后端初始化失败 {backend.name}: {e}")
        
        if not self.clients:
            logger.error("所有后端初始化失败")
    
    def _get_next_client(self) -> Optional[tuple[Backend, OpenAI]]:
        """获取下一个可用的客户端（负载均衡）"""
        if not self.clients:
            return None
        with self.lock:
            idx = self.current_client_index
            client = self.clients[idx]
            # 指针前进，下一次调用返回下一个
            self.current_client_index = (idx + 1) % len(self.clients)
            return client
    
    def generate(
        self,
        messages: List[Dict[str, str]],
        use_cache: bool = True,
        max_retries: int = 3,
        backoff_factor: float = 1.5
    ) -> tuple[bool, str]:
        """
        生成文本（带缓存、重试、速率限制）
        
        Args:
            messages: 消息列表
            use_cache: 是否使用缓存
            max_retries: 最大重试次数
            backoff_factor: 退避因子
        
        Returns:
            (成功标志, 生成内容/错误信息)
        """
        enabled_backends = self.config.get_enabled_backends()
        if not enabled_backends:
            return False, "错误：无有效后端，请检查设置"

        # 参数校验
        if not isinstance(messages, list) or len(messages) == 0:
            return False, "错误：messages 必须是非空列表"

        # 重试逻辑（对不同后端轮询）
        retry_count = 0
        base_wait = 1.0
        
        import random

        while retry_count < max_retries:
            client_info = self._get_next_client()
            if not client_info:
                return False, "错误：无可用的API客户端"

            backend, client = client_info
            model = getattr(backend, "model", None)
            limiter_key = f"{backend.name}_{model}"

            # 确保存在速率限制器
            if limiter_key not in self.rate_limiters:
                self.rate_limiters[limiter_key] = RateLimiter(rate=10, window=60)

            # 尝试使用缓存（以选中的后端 model 为准）
            if use_cache and model:
                cached = self.cache.get(messages, model)
                if cached:
                    return True, cached

            try:
                # 申请令牌（阻塞直到可用）
                self.rate_limiters[limiter_key].acquire(blocking=True)

                logger.debug(f"调用API: {backend.name} model={model}")

                response = client.chat.completions.create(
                    model=model,
                    messages=messages,
                    temperature=getattr(self.config.generation, "temperature", 0.8),
                    top_p=getattr(self.config.generation, "top_p", 1.0),
                    max_tokens=getattr(self.config.generation, "max_tokens", 512)
                )

                # 容错解析响应
                content = ""
                try:
                    content = response.choices[0].message.content.strip()
                except Exception:
                    try:
                        content = response.choices[0].text.strip()
                    except Exception:
                        content = str(response)

                # 缓存结果
                if use_cache and model:
                    self.cache.set(messages, model, content)

                logger.info(f"API调用成功: {backend.name}")
                return True, content

            except RateLimitError as e:
                retry_count += 1
                jitter = random.random() * 0.5
                wait_time = base_wait * (backoff_factor ** retry_count) + jitter
                logger.warning(f"API速率限制 ({backend.name})，等待 {wait_time:.2f}s 后重试... (第{retry_count}次)")
                time.sleep(wait_time)

            except APIError as e:
                retry_count += 1
                jitter = random.random() * 0.5
                wait_time = base_wait * (backoff_factor ** retry_count) + jitter
                logger.warning(f"API错误 ({backend.name}): {e}，等待 {wait_time:.2f}s 重试... (第{retry_count}次)")
                time.sleep(wait_time)

            except Exception as e:
                # 未知错误直接返回，但包含上下文
                logger.exception(f"未预期的错误 ({getattr(backend,'name', 'unknown')}): {e}")
                return False, f"错误：{str(e)}"

        return False, f"错误：在 {max_retries} 次重试后仍然失败"
    
    def test_backends(self) -> Dict[str, bool]:
        """测试所有后端的可用性"""
        results = {}
        test_messages = [
            {"role": "system", "content": "你是一个有帮助的助手"},
            {"role": "user", "content": "你好"}
        ]
        
        for backend in self.config.get_enabled_backends():
            try:
                client = OpenAI(
                    base_url=backend.base_url.rstrip("/"),
                    api_key=backend.api_key,
                    timeout=5
                )
                
                response = client.chat.completions.create(
                    model=backend.model,
                    messages=test_messages,
                    max_tokens=10
                )
                
                results[backend.name] = True
                logger.info(f"后端测试成功: {backend.name}")
            except Exception as e:
                results[backend.name] = False
                logger.error(f"后端测试失败 {backend.name}: {e}")
        
        return results
    
    def clear_cache(self) -> None:
        """清空缓存"""
        self.cache.clear()
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """获取缓存统计"""
        return {
            "total_entries": len(self.cache.cache),
            "max_size": self.cache.max_size,
            "usage_rate": len(self.cache.cache) / self.cache.max_size * 100
        }


# 全局API客户端实例
_api_client: Optional[APIClient] = None


def get_api_client() -> APIClient:
    """获取全局API客户端实例"""
    global _api_client
    if _api_client is None:
        _api_client = APIClient()
    return _api_client


def reinit_api_client() -> None:
    """重新初始化API客户端（配置更改后调用）"""
    global _api_client
    if _api_client is not None:
        _api_client._init_clients()
