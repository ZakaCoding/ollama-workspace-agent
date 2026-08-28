from fastapi import FastAPI
from pydantic import BaseModel, Field

from app.service import AgentService


class ChatRequest(BaseModel):
    message: str = Field(min_length=1)


class ChatResponse(BaseModel):
    content: str
    completed: bool = True


class StatusResponse(BaseModel):
    ready: bool
    chunks: int


class IndexResponse(BaseModel):
    status: str
    ready: bool
    chunks: int


def create_app(service: AgentService | None = None) -> FastAPI:
    agent_service = service or AgentService()
    app = FastAPI(
        title="Local Coding Agent API",
        version="0.1.0",
    )

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/status", response_model=StatusResponse)
    def status() -> StatusResponse:
        return StatusResponse(**agent_service.status())

    @app.post("/chat", response_model=ChatResponse)
    def chat(request: ChatRequest) -> ChatResponse:
        content = agent_service.chat(request.message)
        return ChatResponse(content=content)

    @app.post("/index", response_model=IndexResponse)
    def index() -> IndexResponse:
        agent_service.index()
        return IndexResponse(
            status="ok",
            **agent_service.status(),
        )

    return app


app = create_app()
