import time
import logging

logger = logging.getLogger("timing")

async def timing_middleware(request, call_next):
    start = time.perf_counter()

    response = await call_next(request)

    duration = (time.perf_counter() - start) * 1000

    logger.info(
        f"[TIMING] {request.method} {request.url.path} "
        f"→ {duration:.2f} ms | status={response.status_code}"
    )

    return response
