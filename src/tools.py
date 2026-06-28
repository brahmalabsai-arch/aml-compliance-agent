"""
tools.py — The three tools the agent can call.

1. rag_search        -> retrieves AML/KYC policy clauses (local ChromaDB)
2. screen_sanctions  -> live sanctions screening (OpenSanctions API)
3. get_fx_rate       -> live currency->USD conversion (open.er-api.com)

Each function returns a plain dict so it serializes cleanly with json.dumps()
when handed back to the LLM as a tool result.
"""
import os
# Quiet the Hugging Face download/progress noise before heavy imports load
os.environ.setdefault("HF_HUB_DISABLE_PROGRESS_BARS", "1")
os.environ.setdefault("HF_HUB_DISABLE_TELEMETRY", "1")
os.environ.setdefault("TRANSFORMERS_VERBOSITY", "error")
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
import requests
import chromadb
from chromadb.utils import embedding_functions

DB_DIR = os.path.join(os.path.dirname(__file__), "..", "chroma_db")
COLLECTION = "aml_policies"
OS_BASE = os.getenv("OPENSANCTIONS_BASE", "https://api.opensanctions.org")

# Currency hint per high-risk / common destination (demo simplification)
_COUNTRY_CCY = {
    "iran": "IRR", "syria": "SYP", "cuba": "CUP", "myanmar": "MMK",
    "germany": "EUR", "france": "EUR", "india": "INR", "uk": "GBP",
    "united kingdom": "GBP", "japan": "JPY", "brazil": "BRL",
}


def _collection():
    client = chromadb.PersistentClient(path=DB_DIR)
    embed_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
        model_name="all-MiniLM-L6-v2"
    )
    return client.get_collection(COLLECTION, embedding_function=embed_fn)


def rag_search(query: str, k: int = 3) -> dict:
    """Retrieve the most relevant AML/KYC policy clauses for a query."""
    col = _collection()
    res = col.query(query_texts=[query], n_results=k)
    hits = []
    for doc, meta in zip(res["documents"][0], res["metadatas"][0]):
        hits.append({
            "source": meta["source"],
            "section": meta["section"],
            "text": doc.strip(),
        })
    return {"query": query, "clauses": hits}


def screen_sanctions(name: str, country: str = "") -> dict:
    """Screen a counterparty name against live sanctions lists via OpenSanctions.

    Returns the top match with a score. Caller decides BLOCK vs REVIEW based on
    whether the match is a confident hit (policy 3.1) or fuzzy (policy 3.2).

    Requires a free OpenSanctions API key in the OPENSANCTIONS_API_KEY env var.
    Get one at https://www.opensanctions.org/api/
    """
    os_key = os.getenv("OPENSANCTIONS_API_KEY", "")  # read at call time, not import time
    if not os_key:
        return {
            "name": name,
            "match": None,
            "error": "No OPENSANCTIONS_API_KEY set. Get a free key at "
                     "https://www.opensanctions.org/api/ and add it to .env",
        }
    try:
        # query-by-example: describe the entity, API returns ranked candidates
        payload = {"queries": {"q1": {"schema": "Company", "properties": {"name": [name]}}}}
        headers = {"Authorization": f"ApiKey {os_key}"}
        r = requests.post(
            f"{OS_BASE}/match/default",
            json=payload,
            headers=headers,
            params={"algorithm": "best"},
            timeout=20,
        )
        r.raise_for_status()
        results = r.json()["responses"]["q1"]["results"]
        if not results:
            return {"name": name, "match": False, "score": 0.0,
                    "matched_entity": None, "topics": []}
        top = results[0]
        score = round(top["score"], 3)
        topics = top.get("properties", {}).get("topics", [])

        # A high name score alone is NOT a sanctions hit. OpenSanctions aggregates
        # many list types (sanctions, PEPs, regulatory actions, company registries).
        # We must check WHAT KIND of entity matched, via its 'topics' tags:
        #   'sanction' / 'sanction.linked'  -> actual sanctions designation
        #   'role.pep' / 'role.rca'         -> politically exposed person
        #   'reg.action' / 'reg.warn' etc.  -> regulatory action (e.g. a fine)
        is_sanctioned = any(t in ("sanction", "sanction.linked") for t in topics)
        is_other_risk = bool(topics) and not is_sanctioned

        if is_sanctioned and score >= 0.85:
            match_level = "confident_sanction"      # -> BLOCK
        elif is_sanctioned and score >= 0.70:
            match_level = "fuzzy_sanction"          # -> REVIEW (possible false positive)
        elif is_other_risk and score >= 0.70:
            match_level = "other_risk"              # -> REVIEW (PEP/regulatory, not a ban)
        else:
            match_level = "none"                    # name match but no risk topic -> clean

        return {
            "name": name,
            "match": match_level != "none",
            "match_level": match_level,
            "score": score,
            "matched_entity": top.get("caption"),
            "topics": topics,
            "lists": top.get("datasets", [])[:5],
        }
    except Exception as e:
        return {"name": name, "error": str(e), "match": None}


EDD_THRESHOLD_USD = 10_000  # policy 2.1: payments at/above this need review


def get_fx_rate(amount: float, currency: str = "USD", country: str = "") -> dict:
    """Convert an amount into USD so it can be checked against the policy's
    USD-denominated thresholds (e.g. the USD 10,000 EDD line).

    Uses open.er-api.com, a free keyless exchange-rate API. It returns rates
    relative to a base currency; we fetch rates based on the payment currency
    and read the USD rate from the table.

    The policy thresholds are written in USD, so whatever currency the payment
    is in, we normalize it to USD here. If currency is omitted we infer it from
    the destination country.

    IMPORTANT: this tool performs the threshold comparison in Python and returns
    an explicit `over_threshold` boolean. We do NOT ask the language model to
    compare numbers itself — LLMs are unreliable at arithmetic, so the code does
    the math and the model just reads the flag. If the conversion fails, we
    return an explicit error rather than a misleading 0.
    """
    ccy = (currency or _COUNTRY_CCY.get(country.lower().strip(), "USD")).upper()

    def _result(amount_usd, rate):
        return {
            "amount_original": amount,
            "currency": ccy,
            "amount_usd": round(amount_usd, 2),
            "rate": rate,
            "threshold_usd": EDD_THRESHOLD_USD,
            "over_threshold": round(amount_usd, 2) >= EDD_THRESHOLD_USD,
        }

    if ccy == "USD":
        return _result(amount, 1.0)
    try:
        # open.er-api.com is free and needs no API key.
        r = requests.get(f"https://open.er-api.com/v6/latest/{ccy}", timeout=15)
        r.raise_for_status()
        data = r.json()
        if data.get("result") != "success":
            return {"amount_original": amount, "currency": ccy,
                    "error": f"FX API returned: {data.get('result', 'unknown error')}"}
        usd_rate = data.get("rates", {}).get("USD")
        if not usd_rate:
            return {"amount_original": amount, "currency": ccy,
                    "error": f"No USD rate available for {ccy}"}
        return _result(amount * usd_rate, round(usd_rate, 6))
    except Exception as e:
        return {"amount_original": amount, "currency": ccy, "error": str(e)}


# Tool schemas exposed to the LLM (Groq / OpenAI-compatible function calling)
TOOL_SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "rag_search",
            "description": "Retrieve relevant internal AML/KYC policy clauses. Use this to find the RULE that applies before making any decision.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "What policy question to look up, e.g. 'threshold for high-risk jurisdiction payments'"},
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "screen_sanctions",
            "description": "Screen a counterparty name against LIVE sanctions lists (OFAC/EU/UN/UK). Always call this before approving any payment.",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "Counterparty legal name"},
                    "country": {"type": "string", "description": "Destination country"},
                },
                "required": ["name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_fx_rate",
            "description": "Convert a payment amount into USD using a LIVE exchange rate, so it can be checked against the policy's USD thresholds. ALWAYS extract the currency from the request: 'INR 800000' means amount=800000, currency='INR'; 'USD 500' means amount=500, currency='USD'. The currency is the 3-letter code stated before the amount. Do NOT default to USD unless the request explicitly says USD or gives a bare '$'.",
            "parameters": {
                "type": "object",
                "properties": {
                    "amount": {"type": "number", "description": "The numeric payment amount, e.g. 800000"},
                    "currency": {"type": "string", "description": "ISO 4217 code of the payment currency as stated in the request, e.g. 'INR', 'EUR', 'USD'. Read it directly from the request text."},
                    "country": {"type": "string", "description": "Destination country (used only as a fallback to infer currency if it truly cannot be read from the request)"},
                },
                "required": ["amount", "currency"],
            },
        },
    },
]

TOOL_REGISTRY = {
    "rag_search": rag_search,
    "screen_sanctions": screen_sanctions,
    "get_fx_rate": get_fx_rate,
}