"""Bound both declared and chunked request bodies before application processing."""

from tempfile import SpooledTemporaryFile

from starlette.responses import JSONResponse


class BodyLimits:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)
        limit = 21 * 1024 * 1024 if scope["path"].startswith("/api/upload") else 2 * 1024 * 1024
        headers = dict(scope.get("headers", []))
        try:
            length = int(headers.get(b"content-length", b"0"))
        except ValueError:
            return await JSONResponse({"detail": "Invalid content length"}, 400)(
                scope, receive, send
            )
        if length > limit:
            return await JSONResponse({"detail": "Request body is too large."}, 413)(
                scope, receive, send
            )
        if scope.get("method") in {"GET", "HEAD", "OPTIONS"}:
            return await self.app(scope, receive, send)
        # Reject before a JSON/multipart parser can turn an overflow into a 400.
        # Spooling bounds memory while retaining the normal ASGI body interface.
        with SpooledTemporaryFile(max_size=1024 * 1024) as body:
            size = 0
            while True:
                message = await receive()
                if message["type"] == "http.disconnect":
                    return
                chunk = message.get("body", b"")
                size += len(chunk)
                if size > limit:
                    return await JSONResponse({"detail": "Request body is too large."}, 413)(
                        scope, receive, send
                    )
                try:
                    body.write(chunk)
                except OSError:
                    return await JSONResponse({"detail": "Temporary storage unavailable."}, 503)(
                        scope, receive, send
                    )
                if not message.get("more_body", False):
                    break
            body.seek(0)
            remaining = size

            async def replay_receive():
                nonlocal remaining
                if remaining == 0:
                    return await receive()
                chunk = body.read(65536)
                remaining -= len(chunk)
                return {"type": "http.request", "body": chunk, "more_body": remaining > 0}

            # Empty bodies still require one request message for downstream parsers.
            if size == 0:

                async def empty_receive():
                    return {"type": "http.request", "body": b"", "more_body": False}

                await self.app(scope, empty_receive, send)
            else:
                await self.app(scope, replay_receive, send)
