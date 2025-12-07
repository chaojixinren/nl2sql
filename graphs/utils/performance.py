import time
from functools import wraps
from typing import Dict, List

# 全局性能数据存储
_performance_data: Dict[str, List[dict]] = {}

def monitor_performance(func):
    """性能监控装饰器 - 记录到 state 和全局存储"""
    @wraps(func)
    def wrapper(state):
        session_id = state.get("session_id", "unknown")
        node_name = func.__name__
        
        start = time.time()
        result = func(state)
        elapsed = time.time() - start
        
        # 记录性能数据
        perf_entry = {
            "node": node_name,
            "elapsed_ms": round(elapsed * 1000, 2),
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
        }
        
        # 打印
        print(f"⏱️  {node_name} took {elapsed:.3f}s")
        
        # 存入全局（用于统计）
        if session_id not in _performance_data:
            _performance_data[session_id] = []
        _performance_data[session_id].append(perf_entry)
        
        # 存入 state（用于追踪）
        if isinstance(result, dict):
            perf_trace = result.get("_performance_trace", [])
            perf_trace.append(perf_entry)
            result["_performance_trace"] = perf_trace
        
        return result
    return wrapper


def get_performance_summary(session_id: str) -> dict:
    """获取某个 session 的性能摘要"""
    data = _performance_data.get(session_id, [])
    if not data:
        return {"total_ms": 0, "nodes": []}
    
    total_ms = sum(d["elapsed_ms"] for d in data)
    return {
        "total_ms": round(total_ms, 2),
        "nodes": data,
        "slowest": max(data, key=lambda x: x["elapsed_ms"])
    }
