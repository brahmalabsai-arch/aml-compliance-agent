"""
agent.py — The tool-calling agent loop.

Flow:
  1. User asks a payment question.
  2. LLM decides which tools to call (rag_search, screen_sanctions, get_fx_rate).
  3. We execute the tools and feed results back.
  4. LLM reasons over the rule (RAG) + live data (API) and returns
     a structured ALLOW / REVIEW / BLOCK decision with rationale.
"""
import os
import json
from dotenv import load_dotenv
from groq import Groq
from tools import TOOL_SCHEMAS, TOOL_REGISTRY

load_dotenv()
client = Groq(api_key=os.getenv("GROQ_API_KEY"))
MODEL = "llama-3.3-70b-versatile"

SYSTEM_PROMPT = """You are an AML compliance decision agent.
For every payment request you MUST:
  1. Call rag_search to find the policy rule(s) that apply.
  2. Call screen_sanctions on the counterparty.
  3. Call get_fx_rate if the amount/threshold matters.
Only after gathering this evidence, return a final decision.

Your final answer MUST be valid JSON only, no prose, in this shape:
{
  "decision": "ALLOW" | "REVIEW" | "BLOCK",
  "rationale": "one or two sentences",
  "policy_clauses_applied": ["AML §X.X", ...],
  "evidence": {"sanctions": ..., "fx": ...}
}

Decision rules (from policy):
- screen_sanctions returns a "match_level" plus the matched entity's "topics".
  A high name score ALONE is not a sanctions hit — what matters is the topic:
  - "confident_sanction" (real sanction topic, score >= 0.85) -> BLOCK.
  - "fuzzy_sanction" (real sanction topic, score 0.70-0.85) -> REVIEW. Possible
    false positive; an analyst must confirm it is the same entity (policy 3.2).
  - "other_risk" (matched a PEP or regulatory-action entry, NOT a sanctions
    list) -> REVIEW, never BLOCK. Being a PEP or having a regulatory record is
    not the same as being sanctioned. Note the topics in your rationale.
  - "none" (name matched but no risk topic, or no match) -> no sanctions concern.
- Amount threshold: get_fx_rate returns an "over_threshold" boolean (the code
  already did the math — do NOT compare the numbers yourself). If
  "over_threshold" is true, that satisfies the >= USD 10,000 rule -> REVIEW
  (if not already BLOCK). If it is false, the amount is BELOW the threshold and
  does NOT trigger review on its own.
- High-risk jurisdiction -> REVIEW (if not already BLOCK).
- If the sanctions check could not run (returned an "error"), you CANNOT
  confirm the entity is clean, so never ALLOW. Fall back to REVIEW at minimum,
  and note in the rationale that sanctions screening was unavailable.
- Otherwise -> ALLOW.
"""


def run(user_query: str, max_turns: int = 6) -> str:
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_query},
    ]

    for _ in range(max_turns):
        resp = client.chat.completions.create(
            model=MODEL,
            messages=messages,
            tools=TOOL_SCHEMAS,
            tool_choice="auto",
            temperature=0,
        )
        msg = resp.choices[0].message

        if not msg.tool_calls:
            return msg.content  # final JSON decision

        # Append the assistant's tool-call message
        messages.append({
            "role": "assistant",
            "content": msg.content or "",
            "tool_calls": [
                {
                    "id": tc.id,
                    "type": "function",
                    "function": {"name": tc.function.name, "arguments": tc.function.arguments},
                }
                for tc in msg.tool_calls
            ],
        })

        # Execute each requested tool and feed results back
        for tc in msg.tool_calls:
            fn = TOOL_REGISTRY[tc.function.name]
            args = json.loads(tc.function.arguments)
            result = fn(**args)
            messages.append({
                "role": "tool",
                "tool_call_id": tc.id,
                "name": tc.function.name,
                "content": json.dumps(result),  # serialize tool result cleanly
            })

    return '{"decision": "REVIEW", "rationale": "Max reasoning turns reached."}'


DEMO_QUERIES = [
    "Approve a payment of USD 500 to 'Bright Future Trading Ltd' in Germany?",
    "Approve a payment of INR 800000 to 'Reliance Industries' in India?",
    "Approve a payment of USD 50,000 to 'Pars Petrochemical' in Iran?",
]

if __name__ == "__main__":
    for q in DEMO_QUERIES:
        print("=" * 70)
        print("QUERY:", q)
        print("-" * 70)
        print(run(q))
        print()