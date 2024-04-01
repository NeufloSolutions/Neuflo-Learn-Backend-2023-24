import logging
import time
from fastapi import Request
from typing import Callable

from starlette.types import ASGIApp, Scope, Receive, Send

logger = logging.getLogger(__name__)

class LogLatencyMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope['type'] == 'http':
            start_time = time.time()
            request = Request(scope, receive=receive)  # Create a Request object
            print(f"Request: {request.method} {request.url.path} started")  # Logging request start
            logger.info(f"Request: {request.method} {request.url.path} started")
            await self.app(scope, receive, send)  # Call the next app in the middleware stack
            process_time = time.time() - start_time
            print(f"Request: {request.method} {request.url.path} completed in {process_time} seconds")  # Logging request completion
            logger.info(f"Request: {request.method} {request.url.path} completed in {process_time} seconds")
        else:
            await self.app(scope, receive, send)  # Non-HTTP requests are passed through
