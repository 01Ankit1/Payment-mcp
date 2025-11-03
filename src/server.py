import contextlib

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from src.auth import AuthMiddleware
from src.config import settings
from src.mcp import create_streamable_http_app, mcp

mcp_app = create_streamable_http_app()


@contextlib.asynccontextmanager
async def lifespan(app: FastAPI):
    async with mcp.session_manager.run():
        yield


app = FastAPI(lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    return {"status": "ok", "service": "payment-mcp"}


@app.get("/.well-known/oauth-protected-resource/mcp")
async def oauth_protected_resource_metadata():
    try:
        return settings.metadata_response()
    except ValueError as exc:
        return JSONResponse(
            status_code=500,
            content={
                "error": "invalid_metadata_configuration",
                "error_description": str(exc),
            },
        )


app.add_middleware(AuthMiddleware)
app.mount("/mcp", mcp_app)


def main() -> None:
    uvicorn.run(app, host="0.0.0.0", port=settings.PORT)


if __name__ == "__main__":
    main()
