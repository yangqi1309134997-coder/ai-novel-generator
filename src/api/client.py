"""
统一API客户端 - 支持多提供商、重试、缓存、速率限制

版权所有 © 2026 新疆幻城网安科技有限责任公司 (幻城科技)
作者：幻城
"""

import time
import hashlib
import json
import logging
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from functools import wraps
import threading

from openai import OpenAI, RateLimitError, APIError

from ..config.providers import ProviderFactory, ProviderConfig, PRESET_PROVIDERS
from ..utils.api_logger import get_api_logger

logger = logging.getLogger(__name__)

# 缓存目录
CACHE_DIR = Path("cache/api")
CACHE_DIR.mkdir(parents=True, exist_ok=True)

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

    def __init__(self, max_size: int = MAX_CACHE_SIZE, cache_dir: Path = CACHE_DIR):
        self.cache: Dict[str, CacheEntry] = {}
        self.max_size = max_size
        self.cache_dir = cache_dir
        self.lock = threading.Lock()
        self._load_from_disk()

    def _generate_key(self, messages: List[Dict], model: str) -> str:
        """生成缓存key"""
        content = json.dumps(messages, sort_keys=True, ensure_ascii=False) + model
        return hashlib.md5(content.encode('utf-8')).hexdigest()

    @staticmethod
    def _is_invalid_cached_value(value: str) -> bool:
        """Reject SDK repr strings and empty cache entries."""
        if not value:
            return True

        text = str(value).strip()
        if not text:
            return True

        return text.startswith("ChatCompletion(") or "ChatCompletionMessage(" in text

    def get(self, messages: List[Dict], model: str) -> Optional[str]:
        """获取缓存"""
        key = self._generate_key(messages, model)

        with self.lock:
            if key in self.cache:
                entry = self.cache[key]
                # 检查是否过期
                if datetime.now() - entry.timestamp < timedelta(seconds=entry.ttl):
                    logger.debug(f"缓存命中: {key}")
                    if self._is_invalid_cached_value(entry.value):
                        del self.cache[key]
                        return None
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

            if self._is_invalid_cached_value(value):
                return

            self.cache[key] = CacheEntry(
                key=key,
                value=value,
                timestamp=datetime.now(),
                ttl=ttl
            )
            logger.debug(f"缓存设置: {key}")

        # 尝试保存到磁盘
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
            cache_file = self.cache_dir / "response_cache.json"
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
            cache_file = self.cache_dir / "response_cache.json"
            if cache_file.exists():
                with open(cache_file, "r", encoding="utf-8") as f:
                    raw = json.load(f)
                loaded: Dict[str, CacheEntry] = {}
                for k, v in raw.items():
                    try:
                        ts = datetime.fromisoformat(v.get("timestamp"))
                    except Exception:
                        ts = datetime.now()
                    value = v.get("value", "")
                    if self._is_invalid_cached_value(value):
                        continue
                    loaded[k] = CacheEntry(
                        key=k,
                        value=value,
                        timestamp=ts,
                        ttl=int(v.get("ttl", 3600))
                    )
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


@dataclass
class ProviderConnection:
    """提供商连接"""
    config: ProviderConfig
    client: OpenAI
    api_key: str
    rate_limiter: RateLimiter
    model: str  # 用户配置的模型
    timeout: int  # 用户配置的超时时间
    max_retries: int  # 用户配置的最大重试次数


class UnifiedAPIClient:
    """
    统一API客户端

    特性：
    1. 支持多提供商切换
    2. 自动重试和退避
    3. 响应缓存
    4. 速率限制
    5. 负载均衡
    """

    def __init__(
        self,
        provider_configs: List[Dict[str, Any]],
        use_cache: bool = True,
        cache_dir: Optional[Path] = None
    ):
        """
        初始化API客户端

        Args:
            provider_configs: 提供商配置列表
                [{
                    "provider_id": "openai",  # 预设提供商ID
                    "api_key": "sk-...",
                    "base_url": "https://...",  # 可选，覆盖默认
                    "model": "gpt-4o",  # 可选
                    "enabled": True
                }]
            use_cache: 是否使用缓存
            cache_dir: 缓存目录
        """
        self.use_cache = use_cache
        self.cache_dir = cache_dir or CACHE_DIR

        # 缓存管理器
        self.cache = ResponseCache(cache_dir=self.cache_dir)

        # 提供商连接
        self.connections: List[ProviderConnection] = []
        self.current_connection_index = 0
        self.lock = threading.Lock()

        # 初始化连接
        self._init_connections(provider_configs)

    def _init_connections(self, provider_configs: List[Dict[str, Any]]) -> None:
        """初始化所有提供商连接"""
        for config_dict in provider_configs:
            # 跳过禁用的提供商
            if not config_dict.get("enabled", True):
                continue

            provider_id = config_dict.get("provider_id")
            api_key = config_dict.get("api_key", "")

            # 获取预设配置
            preset_config = ProviderFactory.get_provider_config(provider_id)
            if not preset_config:
                logger.warning(f"未找到提供商配置: {provider_id}")
                continue

            # 检查是否需要API Key
            if preset_config.requires_key and not api_key:
                logger.warning(f"提供商 {provider_id} 需要API Key但未提供，跳过")
                continue

            # 使用自定义URL或默认URL
            base_url = config_dict.get("base_url", preset_config.base_url)
            base_url = base_url.rstrip("/")  # 移除尾部斜杠

            # 使用用户配置的模型或默认模型
            user_model = config_dict.get("model", preset_config.default_model)

            # 使用用户配置的超时时间或默认值（60秒）
            user_timeout = config_dict.get("timeout", 60)
            try:
                user_timeout = int(user_timeout)
                if user_timeout < 10:
                    user_timeout = 10  # 最小10秒
                elif user_timeout > 600:
                    user_timeout = 600  # 最大10分钟
            except (ValueError, TypeError):
                user_timeout = 60  # 默认60秒

            # 使用用户配置的重试次数或默认值（3次）
            user_max_retries = config_dict.get("max_retries", 3)
            try:
                user_max_retries = int(user_max_retries)
                if user_max_retries < 0:
                    user_max_retries = 0  # 不重试
                elif user_max_retries > 10:
                    user_max_retries = 10  # 最多10次
            except (ValueError, TypeError):
                user_max_retries = 3  # 默认3次

            try:
                # 创建OpenAI客户端
                client = OpenAI(
                    base_url=base_url,
                    api_key=api_key,
                    timeout=user_timeout
                )

                # 创建速率限制器
                rate_limiter = RateLimiter(rate=10, window=60)

                # 创建连接（保存用户配置的模型、超时和重试次数）
                connection = ProviderConnection(
                    config=preset_config,
                    client=client,
                    api_key=api_key,
                    rate_limiter=rate_limiter,
                    model=user_model,
                    timeout=user_timeout,
                    max_retries=user_max_retries
                )

                self.connections.append(connection)
                logger.info(f"提供商初始化成功: {preset_config.name} (超时: {user_timeout}秒, 重试: {user_max_retries}次)")

            except Exception as e:
                logger.error(f"提供商初始化失败 {preset_config.name}: {e}")

        if not self.connections:
            logger.error("所有提供商初始化失败")

    def _get_next_connection(self) -> Optional[ProviderConnection]:
        """获取下一个可用连接（负载均衡）"""
        if not self.connections:
            return None

        with self.lock:
            idx = self.current_connection_index
            connection = self.connections[idx]
            # 指针前进
            self.current_connection_index = (idx + 1) % len(self.connections)
            return connection

    def generate(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        temperature: float = 0.8,
        max_tokens: int = 4000,
        use_cache: Optional[bool] = None,
        max_retries: Optional[int] = None,
        frequency_penalty: Optional[float] = None,
        presence_penalty: Optional[float] = None
    ) -> str:
        """
        生成文本

        Args:
            messages: 消息列表
            model: 模型名称（可选，使用提供商默认）
            temperature: 温度参数
            max_tokens: 最大token数
            use_cache: 是否使用缓存
            max_retries: 最大重试次数（可选，优先使用配置文件中的值）
            frequency_penalty: 频率惩罚参数（可选，降低重复词汇出现频率）
            presence_penalty: 存在惩罚参数（可选，鼓励引入新话题）

        Returns:
            生成的文本

        Raises:
            Exception: 所有重试失败后抛出异常
        """
        if not self.connections:
            raise Exception("没有可用的API连接")

        use_cache = use_cache if use_cache is not None else self.use_cache

        # 获取当前连接和其配置的重试次数
        connection = self._get_next_connection()
        if not connection:
            raise Exception("无法获取API连接")

        # 如果没有指定max_retries，使用连接的配置
        if max_retries is None:
            max_retries = connection.max_retries

        # 重试逻辑
        retry_count = 0
        last_error = None
        api_logger = get_api_logger()

        while retry_count < max_retries:
            # 优先使用用户配置的模型，其次使用默认模型
            if not model:
                model = connection.model if hasattr(connection, 'model') else connection.config.default_model

            # 尝试使用缓存
            if use_cache:
                cached = self.cache.get(messages, model)
                if cached:
                    logger.debug("使用缓存响应")
                    # 记录缓存命中
                    api_logger.log_exchange(
                        endpoint=f"{connection.config.name} ({model}) [CACHED]",
                        request_data={"messages": messages, "model": model},
                        response_data=cached,
                        duration_ms=0,
                        metadata={"cache_hit": True}
                    )
                    return cached

            start_time = time.time()

            try:
                # 申请令牌
                connection.rate_limiter.acquire(blocking=True)

                logger.debug(f"调用API: {connection.config.name} model={model} (重试 {retry_count+1}/{max_retries})")

                # 准备请求数据用于日志
                request_data = {
                    "model": model,
                    "messages": messages,
                    "temperature": temperature,
                    "max_tokens": max_tokens
                }

                # 调用API
                request_kwargs = {
                    "model": model,
                    "messages": messages,
                    "temperature": temperature,
                    "max_tokens": max_tokens,
                }
                if frequency_penalty is not None:
                    request_kwargs["frequency_penalty"] = frequency_penalty
                if presence_penalty is not None:
                    request_kwargs["presence_penalty"] = presence_penalty
                if "bigmodel.cn" in str(connection.config.base_url) and str(model).startswith("glm-4.7"):
                    request_kwargs["extra_body"] = {"thinking": {"type": "disabled"}}

                response = connection.client.chat.completions.create(**request_kwargs)

                # 计算耗时
                duration_ms = (time.time() - start_time) * 1000

                # 解析响应
                content = self._parse_response(response)

                if not content:
                    raise Exception("API返回空内容")

                # AI套话后处理过滤
                content = self._filter_ai_cliches(content)  # noqa: use the method below

                # 保存到缓存
                if use_cache:
                    self.cache.set(messages, model, content)

                # 记录API采样日志
                api_logger.log_exchange(
                    endpoint=f"{connection.config.name} ({model})",
                    request_data=request_data,
                    response_data=content,
                    duration_ms=duration_ms,
                    metadata={"retry_count": retry_count, "provider": connection.config.name}
                )

                return content

            except RateLimitError as e:
                duration_ms = (time.time() - start_time) * 1000
                logger.warning(f"速率限制: {e}")
                last_error = e
                retry_count += 1

                # 记录错误
                api_logger.log_exchange(
                    endpoint=f"{connection.config.name} ({model})",
                    request_data={"model": model, "messages": messages},
                    duration_ms=duration_ms,
                    error=e,
                    metadata={"retry_count": retry_count, "error_type": "RateLimitError"}
                )

                if retry_count < max_retries:
                    wait_time = 2 ** retry_count  # 指数退避: 2, 4, 8, 16, 32秒
                    logger.info(f"等待 {wait_time} 秒后重试...")
                    time.sleep(wait_time)

            except APIError as e:
                duration_ms = (time.time() - start_time) * 1000
                logger.error(f"API错误: {e}")
                last_error = e
                retry_count += 1

                # 记录错误
                api_logger.log_exchange(
                    endpoint=f"{connection.config.name} ({model})",
                    request_data={"model": model, "messages": messages},
                    duration_ms=duration_ms,
                    error=e,
                    metadata={"retry_count": retry_count, "error_type": "APIError"}
                )

                if retry_count < max_retries:
                    wait_time = 2 ** retry_count
                    logger.info(f"等待 {wait_time} 秒后重试...")
                    time.sleep(wait_time)

            except Exception as e:
                duration_ms = (time.time() - start_time) * 1000
                logger.error(f"生成失败: {e}")
                last_error = e
                retry_count += 1

                # 记录错误
                api_logger.log_exchange(
                    endpoint=f"{connection.config.name} ({model})",
                    request_data={"model": model, "messages": messages},
                    duration_ms=duration_ms,
                    error=e,
                    metadata={"retry_count": retry_count, "error_type": type(e).__name__}
                )

                if retry_count < max_retries:
                    wait_time = 2 ** retry_count
                    logger.info(f"等待 {wait_time} 秒后重试...")
                    time.sleep(wait_time)

        # 所有重试失败
        raise Exception(f"生成失败，已重试{max_retries}次: {last_error}")

    def _filter_ai_cliches(self, text: str) -> str:
        """后处理过滤AI套话，用自然替代词替换"""
        replacements = {
            '深吸一口气': '缓缓吐出一口浊气',
            '眉头紧锁': '眉头微蹙',
            '瞳孔骤缩': '目光一凝',
            '嘴角上扬': '微微勾起唇角',
            '心中涌起': '心底浮上',
            '不由得': '',
            '赫然': '明明白白地',
            '不禁': '',
        }
        for old, new in replacements.items():
            text = text.replace(old, new)
        return text

    def _parse_response(self, response) -> str:
        """
        解析API响应

        Args:
            response: OpenAI响应对象

        Returns:
            解析后的文本内容
        """
        content = ""

        try:
            # 标准OpenAI格式
            if hasattr(response, 'choices') and len(response.choices) > 0:
                choice = response.choices[0]

                if hasattr(choice, 'message') and hasattr(choice.message, 'content'):
                    content = choice.message.content
                    if (not content or len(str(content).strip()) < 10) and hasattr(choice.message, 'reasoning_content'):
                        content = choice.message.reasoning_content
                elif hasattr(choice, 'text'):
                    content = choice.text

            # 如果标准解析失败，尝试其他格式
            if not content or len(content.strip()) < 10:
                if hasattr(response, 'content'):
                    content = response.content

            # 转换为字典
            if not content or len(content.strip()) < 10:
                try:
                    response_dict = response.model_dump() if hasattr(response, 'model_dump') else {}
                    if 'choices' in response_dict and response_dict['choices']:
                        msg = response_dict['choices'][0].get('message', {})
                        content = msg.get('content', '') or msg.get('reasoning_content', '')
                except Exception:
                    pass

            # 最后的fallback
            if not content or len(content.strip()) < 10:
                content = str(response)

            # 验证内容
            if content:
                content = content.strip()

                # 过滤状态消息
                status_messages = [
                    "续写成功", "重写成功", "润色成功", "生成成功",
                    "完成", "done", "success", "OK", "ok"
                ]
                if content in status_messages or len(content) < 10:
                    logger.warning(f"API返回了状态消息或过短内容: {content}")
                    return ""

            return content

        except Exception as e:
            logger.error(f"解析响应失败: {e}")
            return ""

    def clear_cache(self) -> None:
        """清空缓存"""
        self.cache.clear()

    def get_available_models(self) -> Dict[str, List[str]]:
        """
        获取所有可用提供商的模型列表

        Returns:
            {provider_name: [models]}
        """
        result = {}
        for conn in self.connections:
            result[conn.config.name] = conn.config.models
        return result

    def test_connection(self) -> Dict[str, bool]:
        """
        测试所有连接

        Returns:
            {provider_name: is_connected}
        """
        results = {}

        for conn in self.connections:
            try:
                # 发送简单请求测试连接（使用用户配置的模型）
                test_model = conn.model if hasattr(conn, 'model') else conn.config.default_model
                response = conn.client.chat.completions.create(
                    model=test_model,
                    messages=[{"role": "user", "content": "test"}],
                    max_tokens=5
                )
                results[conn.config.name] = True
                logger.info(f"连接测试成功: {conn.config.name}")
            except Exception as e:
                results[conn.config.name] = False
                logger.warning(f"连接测试失败: {conn.config.name} - {e}")

        return results


# 便捷函数
def create_api_client(
    provider_configs: List[Dict[str, Any]],
    use_cache: bool = True
) -> UnifiedAPIClient:
    """
    创建API客户端

    Args:
        provider_configs: 提供商配置列表
        use_cache: 是否使用缓存

    Returns:
        UnifiedAPIClient实例
    """
    return UnifiedAPIClient(provider_configs, use_cache=use_cache)


def get_api_client() -> Optional[UnifiedAPIClient]:
    """
    获取全局API客户端实例（从配置文件）

    Returns:
        UnifiedAPIClient实例，如果配置无效则返回None
    """
    try:
        # 从配置文件加载 - 支持多种路径
        possible_paths = [
            Path("config/user_config.json"),  # 当前目录
            Path(__file__).parent.parent.parent / "config" / "user_config.json",  # 相对于src/api/client.py
            Path.cwd() / "config" / "user_config.json",  # 当前工作目录
        ]

        config_file = None
        for path in possible_paths:
            if path.exists():
                config_file = path
                break

        if not config_file:
            logger.warning(f"未找到配置文件，尝试的路径: {[str(p) for p in possible_paths]}")
            return None

        with open(config_file, 'r', encoding='utf-8') as f:
            data = json.load(f)

        provider_configs = data.get("providers", [])
        if not provider_configs:
            return None

        return create_api_client(provider_configs)

    except Exception as e:
        logger.error(f"加载API客户端失败: {e}")
        return None
