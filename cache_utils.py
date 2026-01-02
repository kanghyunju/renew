# cache_utils.py - 간단한 메모리 캐시
import time
from typing import Any, Optional, Dict

_CACHE: Dict[str, tuple[Any, float]] = {}
_CACHE_TTL = 300  # 5분

def get_cache(key: str) -> Optional[Any]:
    """캐시에서 값 가져오기"""
    if key in _CACHE:
        value, timestamp = _CACHE[key]
        if time.time() - timestamp < _CACHE_TTL:
            return value
        else:
            del _CACHE[key]
    return None

def set_cache(key: str, value: Any):
    """캐시에 값 저장"""
    _CACHE[key] = (value, time.time())

def clear_cache():
    """캐시 초기화"""
    _CACHE.clear()