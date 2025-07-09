import time
from functools import wraps

def benchmark(log_to_file=True):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            start = time.perf_counter()
            result = func(*args, **kwargs)
            end = time.perf_counter()
            elapsed = end - start
            
            print(f"{func.__name__} executed in {elapsed:.4f} seconds")
            
            if log_to_file:
                log_metrics(func.__name__, elapsed)
                
            return result
        return wrapper
    return decorator

def log_metrics(func_name, elapsed_time):
    with open('performance.log', 'a') as f:
        f.write(f"{func_name},{elapsed_time:.4f},{time.strftime('%Y-%m-%d %H:%M:%S')}\n")