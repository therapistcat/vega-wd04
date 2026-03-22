from __future__ import annotations

import json
from uuid import uuid4
from typing import Any

import httpx
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.encoders import jsonable_encoder
from motor.motor_asyncio import AsyncIOMotorDatabase
from pydantic import BaseModel, Field

from app.ai.tools import AgentToolContext, TOOL_SCHEMAS, execute_tool_call
from app.core.config import settings
from app.core.database import get_database
from app.core.security import require_roles


router = APIRouter(prefix="/ai", tags=["ai-agent"])


class AgentQueryRequest(BaseModel):
    query: str = Field(min_length=2, max_length=3000)
    lat: float | None = Field(default=None, ge=-90, le=90)
    lng: float | None = Field(default=None, ge=-180, le=180)
    conversation_id: str | None = None
    channel: str = Field(default="text", max_length=40)


class ToolExecutionRecord(BaseModel):
    tool_name: str
    arguments: dict[str, Any]
    success: bool
    result: Any


class AgentQueryResponse(BaseModel):
    conversation_id: str
    response_text: str
    used_tools: list[ToolExecutionRecord] = []


def _to_json_string(data: Any) -> str:
    return json.dumps(jsonable_encoder(data), ensure_ascii=False)


def _safe_json_loads(raw: str | None) -> dict[str, Any]:
    if not raw:
        return {}
    try:
        loaded = json.loads(raw)
    except json.JSONDecodeError:
        return {}
    if isinstance(loaded, dict):
        return loaded
    return {}


class AIAgentService:
    def __init__(self, *, db: AsyncIOMotorDatabase, current_user: dict[str, Any]) -> None:
        self.db = db
        self.current_user = current_user

    async def _chat_completion(
        self,
        *,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        if not settings.openai_api_key:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="AI agent is not configured. Set OPENAI_API_KEY.",
            )

        endpoint = f"{settings.openai_api_base.rstrip('/')}/chat/completions"
        headers = {
            "Authorization": f"Bearer {settings.openai_api_key}",
            "Content-Type": "application/json",
        }
        payload: dict[str, Any] = {
            "model": settings.ai_agent_model,
            "messages": messages,
            "temperature": settings.ai_agent_temperature,
        }
        if tools:
            payload["tools"] = tools
            payload["tool_choice"] = "auto"

        try:
            async with httpx.AsyncClient(timeout=settings.ai_agent_timeout_seconds) as client:
                response = await client.post(endpoint, headers=headers, json=payload)
                response.raise_for_status()
                return response.json()
        except httpx.HTTPStatusError as exc:
            detail = exc.response.text[:500] if exc.response is not None else str(exc)
            raise HTTPException(status_code=502, detail=f"LLM upstream error: {detail}") from exc
        except httpx.HTTPError as exc:
            raise HTTPException(status_code=502, detail="Unable to reach LLM endpoint") from exc

    async def handle_query(self, request: AgentQueryRequest) -> AgentQueryResponse:
        conversation_id = request.conversation_id or uuid4().hex
        tool_context = AgentToolContext(
            db=self.db,
            current_user=self.current_user,
            request_lat=request.lat,
            request_lng=request.lng,
        )
        used_tools: list[ToolExecutionRecord] = []

        messages: list[dict[str, Any]] = [
            {"role": "system", "content": settings.ai_agent_system_prompt},
            {
                "role": "user",
                "content": (
                    f"User ID: {self.current_user.get('id')}\n"
                    f"Role: {self.current_user.get('role')}\n"
                    f"Channel: {request.channel}\n"
                    f"Context Coordinates: lat={request.lat}, lng={request.lng}\n"
                    f"User Query: {request.query}"
                ),
            },
        ]

        final_response_text = ""

        for _ in range(max(1, settings.ai_agent_max_tool_rounds)):
            completion = await self._chat_completion(messages=messages, tools=TOOL_SCHEMAS)
            choices = completion.get("choices") or []
            if not choices:
                raise HTTPException(status_code=502, detail="Invalid LLM response: missing choices")

            assistant_message = choices[0].get("message") or {}
            tool_calls = assistant_message.get("tool_calls") or []

            if not tool_calls:
                final_response_text = assistant_message.get("content") or ""
                break

            messages.append(
                {
                    "role": "assistant",
                    "content": assistant_message.get("content"),
                    "tool_calls": tool_calls,
                }
            )

            for call in tool_calls:
                function_payload = call.get("function") or {}
                tool_name = function_payload.get("name", "")
                raw_arguments = function_payload.get("arguments")
                parsed_arguments = _safe_json_loads(raw_arguments)

                try:
                    result = await execute_tool_call(
                        tool_name=tool_name,
                        arguments=parsed_arguments,
                        context=tool_context,
                    )
                    record = ToolExecutionRecord(
                        tool_name=tool_name,
                        arguments=parsed_arguments,
                        success=True,
                        result=jsonable_encoder(result),
                    )
                except Exception as exc:
                    result = {"error": str(exc)}
                    record = ToolExecutionRecord(
                        tool_name=tool_name,
                        arguments=parsed_arguments,
                        success=False,
                        result=result,
                    )

                used_tools.append(record)
                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": call.get("id"),
                        "name": tool_name,
                        "content": _to_json_string(result),
                    }
                )

        if not final_response_text:
            summary_messages = messages + [
                {
                    "role": "user",
                    "content": (
                        "Provide a concise user-friendly final response based on the tool results. "
                        "If complaint was created, include complaint id and current status."
                    ),
                }
            ]
            completion = await self._chat_completion(messages=summary_messages, tools=None)
            choices = completion.get("choices") or []
            if choices:
                final_response_text = choices[0].get("message", {}).get("content") or ""

        if not final_response_text:
            if used_tools:
                final_response_text = "Request processed. Please check tool results."
            else:
                final_response_text = "I could not process your request right now."

        return AgentQueryResponse(
            conversation_id=conversation_id,
            response_text=final_response_text,
            used_tools=used_tools,
        )


@router.post("/query", response_model=AgentQueryResponse)
async def query_agent(
    payload: AgentQueryRequest,
    current_user: dict = Depends(require_roles(["citizen", "authority", "admin"])),
    db: AsyncIOMotorDatabase = Depends(get_database),
) -> AgentQueryResponse:
    service = AIAgentService(db=db, current_user=current_user)
    return await service.handle_query(payload)
