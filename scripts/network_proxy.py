"""Local-only slow/buffering proxy for browser verification, not deployment tooling."""

import asyncio
import os

import httpx
from fastapi import FastAPI, Request
from starlette.responses import StreamingResponse

app = FastAPI()
TARGET = os.environ.get("PROXY_TARGET", "http://127.0.0.1:8010")
DELAY = float(os.environ.get("PROXY_DELAY", "0.15"))
BUFFER = float(os.environ.get("PROXY_BUFFER_SECONDS", "0"))


@app.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"])
async def proxy(path: str, request: Request):
    client = httpx.AsyncClient(timeout=httpx.Timeout(240, connect=10), follow_redirects=False)
    headers = {
        key: value
        for key, value in request.headers.items()
        if key.lower() not in {"host", "content-length", "accept-encoding"}
    }
    # This local proxy forwards an allowed browser origin as the local upstream origin.
    if "origin" in headers:
        headers["origin"] = TARGET
    outbound = client.build_request(
        request.method,
        f"{TARGET}/{path}",
        params=request.query_params,
        headers=headers,
        content=await request.body(),
    )
    response = await client.send(outbound, stream=True)
    streamed = "text/event-stream" in response.headers.get("content-type", "")

    async def chunks():
        try:
            if streamed and BUFFER:
                await asyncio.sleep(BUFFER)
            async for value in response.aiter_bytes():
                if streamed:
                    # Deliberately split bytes across JSON and UTF-8 boundaries.
                    for start in range(0, len(value), 37):
                        await asyncio.sleep(DELAY)
                        yield value[start : start + 37]
                else:
                    yield value
        finally:
            await response.aclose()
            await client.aclose()

    returned = {
        key: value
        for key, value in response.headers.items()
        if key.lower() not in {"content-encoding", "content-length", "transfer-encoding"}
    }
    return StreamingResponse(chunks(), status_code=response.status_code, headers=returned)
