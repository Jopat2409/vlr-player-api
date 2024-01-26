from time import perf_counter


def timer(func):
    def inner(*args, **kwargs):
        start_time = perf_counter()
        v = func(*args, **kwargs)
        etime = perf_counter() - start_time
        print(f"Function {func.__name__} took {etime}s to run")
        return v
    return inner