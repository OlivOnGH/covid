import asyncio, functools, time
from contextlib import contextmanager


def timer(title=None):
    # On peut remplacer le nom de la fonction par un autre titre plus explicite.
    def timer_(func):
        inner_title = func.__name__ if title is None else title
        @contextmanager
        def wrapping_logic():
            start_ts = time.time()
            yield
            dur = time.time() - start_ts
            print(f'{inner_title} exécuté en {dur:.2} secondes.')

        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            if not asyncio.iscoroutinefunction(func):
                with wrapping_logic():
                    return func(*args, **kwargs)
            else:
                async def tmp():
                    with wrapping_logic():
                        return (await func(*args, **kwargs))
                return tmp()
        return wrapper
    return timer_
