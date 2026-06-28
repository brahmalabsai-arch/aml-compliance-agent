"""
fx_debug.py — Test the FX conversion directly, with no LLM involved.

This isolates whether the problem is the conversion (the tool) or the agent
(the LLM). Run:  python src/fx_debug.py
"""
import sys, os, json
sys.path.insert(0, os.path.dirname(__file__))
from dotenv import load_dotenv
load_dotenv()
from tools import get_fx_rate

print("Testing get_fx_rate directly (no LLM):\n")

tests = [
    {"amount": 800000, "currency": "INR", "country": "India"},   # the Reliance case, explicit INR
    {"amount": 800000, "country": "India"},                       # currency inferred from country
    {"amount": 800000, "currency": "USD"},                        # WRONG: treats it as USD
    {"amount": 500, "currency": "USD"},                           # small clean case
]

for t in tests:
    result = get_fx_rate(**t)
    print(f"INPUT : {t}")
    print(f"OUTPUT: {json.dumps(result)}")
    print("-" * 60)