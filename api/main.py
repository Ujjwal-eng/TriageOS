"""
api/main.py
 
FastAPI wrapper around graph. Three endpoints:
 
  POST /tickets                     - submit a new ticket
  GET  /tickets/{ticket_id}         - check status (resolved / pending review)
  POST /tickets/{ticket_id}/review  - a human resumes a paused ticket
 
DESIGN NOTE: the graph and its MCP tool connections are built ONCE at
startup (see `lifespan` below), not per-request. Reconnecting to 3 MCP
server subprocesses on every single API call would be slow and wasteful
— same reasoning as why mcp_client_config.load_all_tools() was always
meant to run once, not per-ticket.

uvicorn api.main:app --reload
"""
 
import uuid
from contextlib import asynccontextmanager
from typing import Optional
 
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from langgraph.types import Command
 
from mcp_client_config import load_all_tools
from graph.builder_graph import build_graph
 
# Holds the built graph after startup — simple module-level dict instead
# of a global variable, so it's easy to see everywhere it's touched.
app_state: dict = {}
 
 
@asynccontextmanager
async def lifespan(app: FastAPI):
    tools_by_server = await load_all_tools()
    app_state["graph"] = build_graph(tools_by_server)
    print("MCP servers connected, graph built. API ready.")
    yield
    app_state.clear()
 
 
app = FastAPI(title="TriageOS API", lifespan=lifespan)

class TicketIn(BaseModel):
    text: str
    ticket_id: Optional[str] = None  # auto-generated if not provided
 
 
class ReviewDecision(BaseModel):
    action: str                            # "approve" | "reject" | "edit" | "manual_resolution"
    text: Optional[str] = None             # used by manual_resolution
    edited_action: Optional[dict] = None   # used by edit
 
 
def _extract_pending_review(result: dict) -> Optional[dict]:
    """If the graph is currently paused at human_review, pull out the
    payload a reviewer needs to see. Returns None if not paused."""
    if "__interrupt__" not in result:
        return None 
    return result["__interrupt__"][0].value

def _build_response(ticket_id: str, result: dict) -> dict:
    """Shared shape for all 3 endpoints — ALWAYS includes category and
    confidence, whether resolved or paused."""
    base = {
        "ticket_id": ticket_id,
        "category": result.get("category"),
        "confidence": result.get("confidence"),
    }
    pending = _extract_pending_review(result)
    if pending:
        return {**base, "status": "pending_human_review", "review_needed": pending}
    return {**base, "status": "resolved", "resolution": result.get("resolution")}

@app.post("/tickets")
async def submit_ticket(ticket: TicketIn):
    ticket_id = ticket.ticket_id or str(uuid.uuid4())
    graph = app_state["graph"]
    config = {"configurable": {"thread_id": ticket_id}}
 
    initial_state = {"messages": [("human", ticket.text)], "ticket_id": ticket_id}
    result = await graph.ainvoke(initial_state, config=config)
 
    return _build_response(ticket_id, result)
 
 
@app.get("/tickets/{ticket_id}")
async def get_ticket_status(ticket_id: str):
    graph = app_state["graph"]
    config = {"configurable": {"thread_id": ticket_id}}
 
    state = await graph.aget_state(config)
    if state is None or not state.values:
        raise HTTPException(status_code=404, detail="Ticket not found")
 
    if state.next:  # graph is paused, waiting at a node
        pending = None
        for task in state.tasks:
            if task.interrupts:
                pending = task.interrupts[0].value
                break
        return {"ticket_id": ticket_id,
            "status": "pending_human_review",
            "review_needed": pending,
            "category": state.values.get("category"),
            "confidence": state.values.get("confidence"),
            }
 
    return {"ticket_id": ticket_id,
        "status": "resolved",
        "resolution": state.values.get("resolution"),
        "category": state.values.get("category"),
        "confidence": state.values.get("confidence"),
        }
 
 
@app.post("/tickets/{ticket_id}/review")
async def submit_human_decision(ticket_id: str, decision: ReviewDecision):
    graph = app_state["graph"]
    config = {"configurable": {"thread_id": ticket_id}}
 
    result = await graph.ainvoke(Command(resume=decision.model_dump()), config=config)
 
    return _build_response(ticket_id, result)
 
#Mounted LAST and on purpose. FastAPI/Starlette tries routes in the
# order they were added — the three /tickets routes above get first
# chance to match. Anything that doesn't match one of those (e.g. "/",
# "/style.css", "/app.js") falls through to this, which serves your
# plain HTML/CSS/JS frontend directly. html=True means "/" specifically
# serves static/index.html.
app.mount("/", StaticFiles(directory="static", html=True), name="static")