
from contextlib import asynccontextmanager
import json
from fastapi import FastAPI
from pydantic import BaseModel
from langchain_core.messages import HumanMessage
from .database.memory import create_memory_table
from .graph_agent import graph
from pydantic import Field
from .services.auth_service import register_user, DuplicateEmailError
from .services.auth_service import register_user,login_user,DuplicateEmailError,InvalidCredentialsError
import jwt
from .database.auth import create_users_table
from .database.auth import get_user_by_email, get_user_by_id
from .database.favorites import create_favorites_table
from fastapi import Depends, HTTPException, status
from fastapi.security import (
    HTTPBearer,
    HTTPAuthorizationCredentials
)

from .security import decode_access_token
from .database.auth import get_user_by_email
from fastapi.responses import StreamingResponse
import time
import logging

logger = logging.getLogger(__name__)


# ==========================================
# 1. Application Lifespan
# ==========================================

@asynccontextmanager
async def lifespan(app: FastAPI):

    # Startup
    create_users_table()
    create_memory_table()
    create_favorites_table()
    print("Customer memory table initialized.")
    print("Agentic Shopping Assistant starting...")

    yield

    # Shutdown
    print("Agentic Shopping Assistant shutting down...")


# ==========================================
# 2. Initialize FastAPI
# ==========================================

app = FastAPI(
    title="Agentic Shopping Assistant",
    lifespan=lifespan
)

bearer_scheme = HTTPBearer(auto_error=False)
# ==========================================
# 3. Request Schema
# ==========================================

class ChatRequest(BaseModel):
    message: str
    conversation_id: str


class RegisterRequest(BaseModel):
    email :str
    password:str = Field(min_length=12,max_length=128)

class LoginRequest(BaseModel):
    email: str
    password : str

def get_verified_user_id(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme)
) -> str:

    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required.",
            headers={"WWW-Authenticate": "Bearer"}
        )

    try:
        payload = decode_access_token(credentials.credentials)

    except jwt.InvalidTokenError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired access token.",
            headers={"WWW-Authenticate": "Bearer"}
        ) from exc

    # Get the verified identity from the JWT
    user_id = payload["sub"]

    # Verify that the account still exists in SQLite
    user = get_user_by_id(user_id)

    # Reject deleted or inactive accounts
    if user is None or user["is_active"] != 1:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or inactive account.",
            headers={"WWW-Authenticate": "Bearer"}
        )

    return user["user_id"]
# ==========================================
# 4. Health Check Endpoint
# ==========================================

@app.get("/api/health")
def api_health():

    return {
        "status": "ok",
        "application": "agentic_shopping_assistant"
    }


# ==========================================
# 5. Chat Endpoint
# ==========================================

@app.post("/api/chat")
def chat(
    request: ChatRequest,
    user_id: str = Depends(get_verified_user_id)
):

    config = {
        "recursion_limit": 20,
        "configurable": {
            "thread_id": f"{user_id}:{request.conversation_id}",
            "user_id": user_id
        }
    }

    human_message = HumanMessage(
        content=request.message
    )

    # Invoke LangGraph
    result = graph.invoke(
        {"messages": [human_message]},
        config=config
    )

    # Extract final AI response
    answer = result["messages"][-1].content

    # Extract structured product results
    products = []

    for message in result["messages"]:

        if (
            getattr(message, "type", None) == "tool"
            and getattr(message, "name", None) == "search_product_tool"
        ):

            try:
                tool_result = json.loads(message.content)

                if isinstance(tool_result, list):
                    products.extend(
                        item for item in tool_result
                        if isinstance(item, dict)
                    )

            except (json.JSONDecodeError, TypeError):
                logger.warning(
                    "Could not parse product search tool result"
                )

    # Remove duplicate products by ID
    unique_products = {
        product["id"]: product
        for product in products
        if product.get("id") is not None
    }

    return {
        "conversation_id": request.conversation_id,
        "answer": answer,
        "products": list(unique_products.values())
    }


@app.post(
    "/api/auth/register",
    status_code=status.HTTP_201_CREATED
)
def register(request: RegisterRequest):

    # 1. Extract user input
    email = request.email
    password = request.password

    try:

        # 2. Call registration service
        new_user = register_user(email, password)

        # 3. Return successful registration
        return {
            "message": "Account created successfully",
            "user": new_user
        }

    except DuplicateEmailError as exc:

        # 4. Handle duplicate email
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc)
        ) from exc

@app.post("/api/auth/login")
def login(request:LoginRequest):
    try:
        #Authenticate customer and generate JWt
        result = login_user(
            request.email,
            request.password
        )

        return result
    
    except InvalidCredentialsError as exc:

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={"WWW-Authenticate":"Baerer"}
        )  from exc


@app.get("/api/auth/verify")
def verify_token(
    user_id: str = Depends(get_verified_user_id)
):
    return {
        "authenticated": True,
        "user_id": user_id
    }


@app.post("/api/chat/stream")
async def chat_stream(
    request: ChatRequest,
    user_id: str = Depends(get_verified_user_id)
):
    config = {
        "recursion_limit": 20,
        "configurable": {
            "thread_id": f"{user_id}:{request.conversation_id}",
            "user_id": user_id
        }
    }

    human_message = HumanMessage(content=request.message)

    def make_event(event_name: str, data: dict):
        return (
            f"event: {event_name}\n"
            f"data: {json.dumps(data, ensure_ascii=False, default=str)}\n\n"
        )

    def get_content(output):
        if hasattr(output, "content"):
            output = output.content

        if isinstance(output, str):
            return output

        if isinstance(output, list):
            text_parts = []

            for block in output:
                if isinstance(block, dict) and block.get("type") == "text":
                    text_parts.append(block.get("text", ""))

            if text_parts:
                return "\n".join(text_parts)

        return str(output) if output is not None else ""

    def parse_tool_output(output):
        if hasattr(output, "content"):
            output = output.content

        if isinstance(output, str):
            try:
                return json.loads(output)
            except json.JSONDecodeError:
                return output

        return output

    def make_preview(result):
        if isinstance(result, list):
            return result[:5]

        if isinstance(result, dict):
            return result

        if isinstance(result, str):
            return result[:1000]

        return str(result)[:1000]

    async def event_stream():

        answer = ""
        products_by_id = {}

        graph_run_id = None

        run_started = {}
        run_details = {}

        yield make_event(
            "request_start",
            {
                "conversation_id": request.conversation_id,
                "message": request.message
            }
        )

        try:

            async for event in graph.astream_events(
                {"messages": [human_message]},
                config=config,
                version="v2"
            ):

                event_name = event.get("event")
                run_id = str(event.get("run_id", ""))
                parent_ids = event.get("parent_ids", [])
                metadata = event.get("metadata", {})
                data = event.get("data", {})

                # ----------------------------------
                # 1. GRAPH START
                # ----------------------------------

                if event_name == "on_chain_start" and not parent_ids:

                    graph_run_id = run_id

                    yield make_event(
                        "graph_start",
                        {
                            "run_id": run_id,
                            "node": event.get("name", "Blink AI")
                        }
                    )

                # ----------------------------------
                # 2. LLM START
                # ----------------------------------

                elif event_name == "on_chat_model_start":

                    run_started[run_id] = time.perf_counter()

                    node_name = metadata.get(
                        "langgraph_node",
                        "llm"
                    )

                    run_details[run_id] = {
                        "node": node_name,
                        "model": event.get("name", "LLM")
                    }

                    yield make_event(
                        "llm_start",
                        {
                            "run_id": run_id,
                            "parent_ids": parent_ids,
                            "node": node_name,
                            "model": event.get("name", "LLM"),
                            "status": "running"
                        }
                    )

                # ----------------------------------
                # 3. LLM END / TOOL CALL DECISION
                # ----------------------------------

                elif event_name == "on_chat_model_end":

                    output = data.get("output")

                    tool_calls = (
                        getattr(output, "tool_calls", None) or []
                    )

                    content = get_content(output)

                    started = run_started.pop(run_id, None)

                    duration_ms = (
                        round((time.perf_counter() - started) * 1000)
                        if started is not None
                        else None
                    )

                    details = run_details.pop(run_id, {})
                    node_name = details.get("node", "llm")

                    yield make_event(
                        "llm_end",
                        {
                            "run_id": run_id,
                            "node": node_name,
                            "model": event.get("name", "LLM"),
                            "duration_ms": duration_ms,
                            "decision": (
                                "tool_calls"
                                if tool_calls
                                else "final_response"
                            ),
                            "tool_call_count": len(tool_calls),
                            "status": "completed"
                        }
                    )

                    # Capture actual tool calls generated by the LLM.
                    for call in tool_calls:

                        yield make_event(
                            "tool_call",
                            {
                                "tool_call_id": call.get("id"),
                                "tool": call.get("name"),
                                "arguments": call.get("args", {}),
                                "llm_run_id": run_id
                            }
                        )

                    # Capture final answer from the main LLM node.
                    if node_name == "llm" and not tool_calls and content:
                        answer = content

                # ----------------------------------
                # 4. TOOL START
                # ----------------------------------

                elif event_name == "on_tool_start":

                    run_started[run_id] = time.perf_counter()

                    tool_name = event.get("name", "unknown_tool")
                    tool_input = data.get("input", {})

                    yield make_event(
                        "tool_start",
                        {
                            "run_id": run_id,
                            "parent_ids": parent_ids,
                            "tool": tool_name,
                            "input": tool_input,
                            "status": "running"
                        }
                    )

                # ----------------------------------
                # 5. TOOL END / DATABASE RESULT
                # ----------------------------------

                elif event_name == "on_tool_end":

                    tool_name = event.get("name", "unknown_tool")

                    raw_output = data.get("output")
                    parsed_result = parse_tool_output(raw_output)

                    started = run_started.pop(run_id, None)

                    duration_ms = (
                        round((time.perf_counter() - started) * 1000)
                        if started is not None
                        else None
                    )

                    failed = (
                        isinstance(parsed_result, dict)
                        and bool(parsed_result.get("error"))
                    )

                    if isinstance(parsed_result, list):

                        summary = (
                            f"Found {len(parsed_result)} products."
                        )

                        if tool_name == "search_product_tool":
                            for product in parsed_result:

                                if (
                                    isinstance(product, dict)
                                    and product.get("id") is not None
                                ):
                                    products_by_id[product["id"]] = product

                    elif failed:

                        summary = str(parsed_result.get("error"))

                    else:

                        summary = "Tool execution completed."

                    yield make_event(
                        "tool_end",
                        {
                            "run_id": run_id,
                            "tool": tool_name,
                            "status": "failed" if failed else "completed",
                            "duration_ms": duration_ms,
                            "summary": summary,
                            "result": make_preview(parsed_result)
                        }
                    )

                # ----------------------------------
                # 6. TOOL ERROR
                # ----------------------------------

                elif event_name == "on_tool_error":

                    tool_name = event.get("name", "unknown_tool")
                    error = str(data.get("error", "Tool execution failed."))

                    started = run_started.pop(run_id, None)

                    duration_ms = (
                        round((time.perf_counter() - started) * 1000)
                        if started is not None
                        else None
                    )

                    yield make_event(
                        "tool_end",
                        {
                            "run_id": run_id,
                            "tool": tool_name,
                            "status": "failed",
                            "duration_ms": duration_ms,
                            "summary": error[:500]
                        }
                    )

                # ----------------------------------
                # 7. GRAPH END
                # ----------------------------------

                elif (
                    event_name == "on_chain_end"
                    and run_id == graph_run_id
                ):

                    # Fallback: obtain the final AI message
                    # from the graph's final state.
                    output = data.get("output")

                    if isinstance(output, dict):
                        messages = output.get("messages", [])

                        for message in reversed(messages):

                            if (
                                getattr(message, "type", None) == "ai"
                                and not getattr(message, "tool_calls", None)
                            ):
                                answer = get_content(message)

                                if answer:
                                    break

            # ----------------------------------
            # 8. FINAL RESPONSE
            # ----------------------------------

            unique_products = list(products_by_id.values())

            yield make_event(
                "final",
                {
                    "conversation_id": request.conversation_id,
                    "graph_run_id": graph_run_id,
                    "answer": answer,
                    "products": unique_products
                }
            )

        except Exception:

            logger.exception("Detailed streaming execution failed")

            yield make_event(
                "error",
                {
                    "message": "Blink AI could not complete your request."
                }
            )

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )