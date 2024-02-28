import time
from fastapi import Request
import logging

# Assuming the logger is configured elsewhere to use AzureLogHandler
logger = logging.getLogger(__name__)

class LogLatencyMiddleware:
    async def __call__(self, request: Request, call_next):
        start_time = time.time()
        response = await call_next(request)
        process_time = time.time() - start_time
        # Use logger to log the API call and its latency
        logger.info(f"Request: {request.method} {request.url.path} completed in {process_time} seconds")
        return response
