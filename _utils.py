import asyncio
from functools import wraps


def async_to_sync(func):
    """装饰器: 将异步方法转换为同步方法, 自动处理asyncio.run()"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        return asyncio.run(func(*args, **kwargs))
    return wrapper