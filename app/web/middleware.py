from __future__ import annotations

from collections.abc import Awaitable, Callable

from fastapi import Request, Response


async def no_store_api(
    request: Request,
    call_next: Callable[[Request], Awaitable[Response]],
) -> Response:
    response = await call_next(request)
    if request.url.path.startswith("/api/"):
        response.headers["Cache-Control"] = "no-store"
    return response
