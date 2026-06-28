"""
api.py — FastAPI service layer over the compliance agent.

Exposes the agent as an HTTP API so other systems (a payment platform, a
frontend, another microservice) can screen transactions over the network
instead of running a script by hand.

Run:
    uvicorn api:app --reload --app-dir src
Then open http://127.0.0.1:8000/docs for an interactive, browsable UI.
"""
import json
from fastapi import FastAPI
from pydantic import BaseModel, Field

from agent import run  # reuse the exact same agent loop, unchanged

app = FastAPI(
    title="AML Compliance Agent",
    description="RAG (AML policy) + live sanctions/FX tool-calling. "
                "Decision-support demo, not a certified compliance system.",
    version="1.0.0",
)


class ScreenRequest(BaseModel):
    name: str = Field(..., examples=["Pars Petrochemical"])
    country: str = Field(..., examples=["Iran"])
    amount_usd: float = Field(..., examples=[50000])


class ScreenResponse(BaseModel):
    decision: str
    rationale: str = ""
    policy_clauses_applied: list = []
    evidence: dict = {}
    raw: str = ""


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/screen", response_model=ScreenResponse)
def screen(req: ScreenRequest):
    """Screen a single outbound payment and return an ALLOW/REVIEW/BLOCK verdict."""
    query = (
        f"Approve a payment of USD {req.amount_usd:,.0f} to "
        f"'{req.name}' in {req.country}?"
    )
    result = run(query)
    try:
        parsed = json.loads(result)
        parsed["raw"] = result
        return parsed
    except json.JSONDecodeError:
        # Agent returned prose instead of JSON; surface it safely
        return {"decision": "REVIEW", "rationale": "Unparseable agent output", "raw": result}
