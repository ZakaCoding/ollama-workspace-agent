import os
import secrets

from dotenv import load_dotenv
from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app.service import AgentService


load_dotenv()


class ChatRequest(BaseModel):
    message: str = Field(min_length=1)


class ChatResponse(BaseModel):
    content: str
    completed: bool = True


class RequestMetrics(BaseModel):
    model: str
    streaming: bool
    succeeded: bool
    duration_ms: float
    prompt_tokens: int | None = None
    completion_tokens: int | None = None


class SessionMetrics(BaseModel):
    requests: int
    failed_requests: int
    total_duration_ms: float
    prompt_tokens: int
    completion_tokens: int
    requests_with_usage: int
    last_request: RequestMetrics | None = None


class RuntimeStatus(BaseModel):
    model: str
    context_budget_tokens: int
    evidence_max_chars: int
    max_output_tokens: int
    capabilities: list[str] | None = None
    model_context_tokens: int | None = None
    metrics: SessionMetrics | None = None


class EmbeddingStatus(BaseModel):
    model: str | None = None
    dimensions: int | None = None
    compatible: bool
    reason: str | None = None


class StatusResponse(BaseModel):
    ready: bool
    chunks: int
    runtime: RuntimeStatus | None = None
    embedding: EmbeddingStatus | None = None


class IndexResponse(BaseModel):
    status: str
    ready: bool
    chunks: int


class ClearResponse(BaseModel):
    status: str


def create_app(
    service: AgentService | None = None,
    api_key: str | None = None,
) -> FastAPI:
    agent_service = service or AgentService()
    configured_api_key = (
        api_key if api_key is not None else os.getenv("API_KEY")
    )

    def require_api_key(
        provided_api_key: str | None = Header(
            default=None,
            alias="X-API-Key",
        ),
    ) -> None:
        if configured_api_key is None:
            return

        if provided_api_key is None or not secrets.compare_digest(
            provided_api_key,
            configured_api_key,
        ):
            raise HTTPException(
                status_code=401,
                detail="Invalid or missing API key.",
                headers={"WWW-Authenticate": "ApiKey"},
            )

    app = FastAPI(
        title="Local Coding Agent API",
        version="0.1.0",
    )

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/status", response_model=StatusResponse, response_model_exclude_none=True)
    def status(
        _: None = Depends(require_api_key),
    ) -> StatusResponse:
        return StatusResponse(**agent_service.status())

    @app.post("/chat", response_model=ChatResponse)
    def chat(
        request: ChatRequest,
        _: None = Depends(require_api_key),
    ) -> ChatResponse:
        try:
            content = agent_service.chat(request.message)
        except Exception as exc:
            raise HTTPException(
                status_code=502,
                detail=f"Chat service unavailable: {exc}",
            ) from exc

        return ChatResponse(content=content)

    @app.post("/chat/stream")
    def chat_stream(
        request: ChatRequest,
        _: None = Depends(require_api_key),
    ) -> StreamingResponse:
        try:
            stream = agent_service.chat_stream(request.message)
        except Exception as exc:
            raise HTTPException(
                status_code=502,
                detail=f"Chat service unavailable: {exc}",
            ) from exc

        return StreamingResponse(
            stream,
            media_type="text/plain; charset=utf-8",
        )

    @app.post("/clear", response_model=ClearResponse)
    def clear(
        _: None = Depends(require_api_key),
    ) -> ClearResponse:
        agent_service.clear()
        return ClearResponse(status="ok")

    @app.post("/index", response_model=IndexResponse)
    def index(
        force: bool = False,
        _: None = Depends(require_api_key),
    ) -> IndexResponse:
        try:
            if force:
                agent_service.index(force=True)
            else:
                agent_service.index()
        except Exception as exc:
            raise HTTPException(
                status_code=500,
                detail=f"Indexing failed: {exc}",
            ) from exc

        return IndexResponse(
            status="ok",
            **agent_service.status(),
        )

    return app


app = create_app()
