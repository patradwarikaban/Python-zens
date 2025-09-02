from concurrent.futures import ThreadPoolExecutor
import os

_threadpool_cpus = int(os.cpu_count() / 2)
EXECUTOR = ThreadPoolExecutor(max_workers=max(_threadpool_cpus, 2))
