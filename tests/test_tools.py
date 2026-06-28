"""
test_tools.py — Lightweight checks for tool return shapes.
Run: python -m pytest tests/  (or just python tests/test_tools.py)
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from tools import rag_search, get_fx_rate  # noqa


def test_rag_search_shape():
    out = rag_search("threshold for high-risk jurisdiction")
    assert "clauses" in out and isinstance(out["clauses"], list)
    assert out["clauses"], "expected at least one clause"
    print("rag_search OK:", out["clauses"][0]["section"])


def test_fx_rate_usd_passthrough():
    out = get_fx_rate(1000, "United States")
    assert out["currency"] == "USD" and out["converted"] == 1000
    print("get_fx_rate USD passthrough OK")


if __name__ == "__main__":
    test_rag_search_shape()
    test_fx_rate_usd_passthrough()
    print("All tests passed.")
