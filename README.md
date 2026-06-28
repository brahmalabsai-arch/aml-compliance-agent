# 🛡️ AML Compliance Agent — A RAG + Tool-Calling AI Project

> A beginner-friendly, end-to-end example of an **AI agent** that makes real
> compliance decisions by combining a **knowledge base (RAG)** with **live data
> from the internet (tool calling)**.
>
> This README is written to be read by *anyone* — including people with no
> technical background. It explains not just *what* the project does, but *how*
> it was built, *what went wrong along the way*, and *how each bug was fixed*.
> The mistakes are part of the lesson.

---

## Table of Contents

- [🛡️ AML Compliance Agent — A RAG + Tool-Calling AI Project](#️-aml-compliance-agent--a-rag--tool-calling-ai-project)
  - [Table of Contents](#table-of-contents)
  - [1. What is this project, in plain English?](#1-what-is-this-project-in-plain-english)
  - [2. The core idea: two kinds of knowledge](#2-the-core-idea-two-kinds-of-knowledge)
  - [3. How the pieces fit together](#3-how-the-pieces-fit-together)
  - [4. Every file, explained simply](#4-every-file-explained-simply)
  - [5. What is RAG? What is "chunking"?](#5-what-is-rag-what-is-chunking)
  - [6. What is "tool calling"?](#6-what-is-tool-calling)
  - [7. The debugging journey — bugs we hit and how we fixed them](#7-the-debugging-journey--bugs-we-hit-and-how-we-fixed-them)
    - [🐛 Bug #1 — A file named `inspect.py` broke Python itself](#-bug-1--a-file-named-inspectpy-broke-python-itself)
    - [🐛 Bug #2 — The currency tool converted the wrong direction](#-bug-2--the-currency-tool-converted-the-wrong-direction)
    - [🐛 Bug #3 — The sanctions API returned "401 Unauthorized", then "no key"](#-bug-3--the-sanctions-api-returned-401-unauthorized-then-no-key)
    - [🐛 Bug #4 — The biggest one: it blocked a perfectly good bank](#-bug-4--the-biggest-one-it-blocked-a-perfectly-good-bank)
    - [🐛 Bug #5 — We let the language model do the math (and it got it wrong)](#-bug-5--we-let-the-language-model-do-the-math-and-it-got-it-wrong)
    - [🐛 Bug #6 — A dead API that failed *silently* and returned a believable lie](#-bug-6--a-dead-api-that-failed-silently-and-returned-a-believable-lie)
  - [8. Example outputs](#8-example-outputs)
  - [9. How to run it yourself](#9-how-to-run-it-yourself)
  - [10. Important honesty notes \& limitations](#10-important-honesty-notes--limitations)
  - [11. Tech stack](#11-tech-stack)

---

## 1. What is this project, in plain English?

Imagine a bank or a payment company (like a Stripe or a Wise). Every time it
sends money abroad on a customer's behalf, it is **legally required to check**:

- Is the company we're paying on a government **sanctions list** (a banned list)?
- Is the amount large enough to need extra scrutiny?
- Is the destination country high-risk?

Doing this by hand is slow. This project builds an **AI agent** — a small
program powered by a language model — that does this check automatically and
returns one of three verdicts:

| Verdict | Meaning |
|---|---|
| ✅ **ALLOW** | Payment is fine, release it. |
| ⚠️ **REVIEW** | Something needs a human to look closer. |
| ⛔ **BLOCK** | Stop the payment — it breaks the rules. |

The agent doesn't guess. It looks up the **written policy** and checks **live
government data**, then explains its reasoning.

---

## 2. The core idea: two kinds of knowledge

Every compliance decision needs two very different kinds of information:

| Kind of knowledge | Example | How often it changes | Where it lives |
|---|---|---|---|
| 📖 **The rule** | "Never pay a sanctioned company." | Almost never | A policy document |
| 🌐 **The live fact** | "Is *this* company sanctioned *today*?" | Daily | A government database online |

You **cannot** write today's sanctions list into a document — it changes
constantly. So the agent must do two things and combine them:

1. **Read the rulebook** → this is called **RAG** (explained below).
2. **Check live data** → this is called a **tool call** (explained below).

> The whole project exists to tie these two together:
> *"The rule says X. The live data says Y. Therefore the decision is Z."*
> That is exactly what a human compliance officer does manually.

---

## 3. How the pieces fit together

```
   You ask:  "Can we pay Company X in Country Y the amount Z?"
                              │
                              ▼
                    ┌──────────────────┐
                    │    THE AGENT     │   (a language model that can
                    │  (the "brain")   │    decide which tools to use)
                    └────────┬─────────┘
                             │  decides what info it needs
         ┌───────────────────┼───────────────────┐
         ▼                   ▼                    ▼
 ┌───────────────┐  ┌──────────────────┐  ┌─────────────────┐
 │  rag_search   │  │ screen_sanctions │  │   get_fx_rate   │
 │  (the rule)   │  │  (live ban list) │  │ (live currency) │
 │               │  │                  │  │                 │
 │  ChromaDB +   │  │  OpenSanctions   │  │ exchangerate.   │
 │  policy docs  │  │  API (online)    │  │ host API(online)│
 └───────────────┘  └──────────────────┘  └─────────────────┘
         │                   │                    │
         └───────────────────┼────────────────────┘
                             ▼
              The agent combines all the evidence and returns:
              { "decision": "BLOCK", "rationale": "...", ... }
```

---

## 4. Every file, explained simply

| File | What it is, in one sentence |
|---|---|
| `data/aml_policy.md` | The **rulebook** — a written AML policy (thresholds, banned-country list, what to do for a sanctions hit). |
| `data/kyc_standard.md` | A second rulebook about verifying *who* the counterparty is. |
| `src/ingest.py` | A one-time setup script that reads the rulebooks and makes them **searchable by meaning**. |
| `src/tools.py` | Defines the **three tools** the agent can use (search the rules, check sanctions, convert currency). |
| `src/agent.py` | The **brain** — it talks to the language model, decides which tools to call, and produces the final verdict. |
| `src/api.py` | Wraps the agent in a **web service** so other programs (or a browser) can use it. |
| `src/inspect_store.py` | A helper to **peek inside** the searchable rulebook and see what's stored. |
| `Dockerfile` | A recipe to **package the whole thing** so it runs identically on any computer. |
| `requirements.txt` | The list of software libraries the project needs. |
| `.env` | A private file holding your **secret API keys** (never shared publicly). |

---

## 5. What is RAG? What is "chunking"?

**RAG** stands for *Retrieval-Augmented Generation*. In plain terms:

> Before the AI answers, it first **retrieves** the most relevant pieces of your
> documents, then uses them to **generate** a grounded answer.

It's like an open-book exam: instead of relying on memory, the AI looks up the
exact rule first.

**Chunking** is the prep step. A document is too big to search all at once, so
we split it into smaller pieces called **chunks**. Each chunk becomes searchable.

**Our chunking strategy: section-based.** We split each policy document at every
`## Section` heading, so **one chunk = one complete policy section**.

Why this choice? Policy rules are self-contained. "Section 3 — Sanctions
Screening" is one whole thought. If we'd split by fixed size (say, every 500
characters), we'd cut a rule in half and the search would return meaningless
fragments. Keeping each section whole means the agent always retrieves a
*complete, usable rule*.

You can see the chunks yourself:

```bash
python src/inspect_store.py                       # lists all stored chunks
python src/inspect_store.py "high risk country"   # shows what gets retrieved
```

---

## 6. What is "tool calling"?

A plain language model can only produce text. It **cannot** look up today's
sanctions list or today's exchange rate. **Tool calling** fixes that.

We give the language model a set of "tools" (just normal functions) and
*descriptions* of what each does. The model then **decides on its own** which
tools to call and with what inputs. Our agent has three tools:

| Tool | What it does | Real or fake data? |
|---|---|---|
| `rag_search` | Looks up the relevant policy rule | Synthetic policy (we wrote it) |
| `screen_sanctions` | Checks a name against live sanctions lists | **Real** (OpenSanctions API) |
| `get_fx_rate` | Converts the amount into USD | **Real** (live exchange rates) |

The magic: we don't hard-code "if sanctioned then block." We give the model the
tools and the policy, and *it* works out the sequence — look up the rule, screen
the name, check the amount, then decide. That autonomy is what makes it an
**agent** rather than a rigid script.

---

## 7. The debugging journey — bugs we hit and how we fixed them

> This is the most valuable section. Building the agent was easy; making it
> *correct* took six real bugs. Each one taught a lesson that applies to almost
> any tool-calling project.

---

### 🐛 Bug #1 — A file named `inspect.py` broke Python itself

**What happened:** We created a helper file called `src/inspect.py`. The moment
we ran anything, Python crashed with a strange error:

```
AttributeError: partially initialized module 'inspect' has no attribute 'signature'
(most likely due to a circular import)
```

**Why:** Python has its *own* built-in module called `inspect`. By naming our
file `inspect.py`, we accidentally **shadowed** (hid) the built-in one. When a
library tried to use the real `inspect`, it found our file instead and crashed.

**The fix:** Rename the file.

```diff
- src/inspect.py
+ src/inspect_store.py
```

**Lesson:** Never name your files after Python's built-in modules (`inspect`,
`json`, `email`, `string`, `random`, etc.). It causes confusing crashes.

---

### 🐛 Bug #2 — The currency tool converted the wrong direction

**What happened:** Our policy thresholds are written in **US dollars** (e.g.
"payments over $10,000 need review"). But a payment might come in as ₹2,500,000
(Indian rupees). To check it against the rule, we must convert **rupees → USD**.
Our first version did the opposite — it converted **USD → local currency** —
which was useless for the threshold check.

**The original (wrong) code:**

```python
def get_fx_rate(amount_usd: float, country: str) -> dict:
    """Convert a USD amount to the destination country's currency, live."""
    ccy = _COUNTRY_CCY.get(country.lower().strip(), "USD")
    ...
    params={"from": "USD", "to": ccy, "amount": amount_usd},   # ← wrong direction
```

**The corrected code:**

```python
def get_fx_rate(amount: float, currency: str = "USD", country: str = "") -> dict:
    """Convert an amount INTO USD so it can be checked against the policy's
    USD-denominated thresholds (e.g. the USD 10,000 line)."""
    ccy = (currency or _COUNTRY_CCY.get(country.lower().strip(), "USD")).upper()
    if ccy == "USD":
        return {"amount_original": amount, "currency": "USD",
                "amount_usd": round(amount, 2), "rate": 1.0}
    ...
    params={"from": ccy, "to": "USD", "amount": amount},        # ← convert TO usd
```

**Lesson:** When a tool feeds a rule, make sure it produces the unit the *rule*
expects. The policy thinks in USD, so the tool must output USD.

---

### 🐛 Bug #3 — The sanctions API returned "401 Unauthorized", then "no key"

This bug had **two layers**, and both are common real-world traps.

**Layer A — The API now needs a key.** Our first version called the
OpenSanctions API with no authentication. It used to be open; it now requires a
free API key. The result:

```json
"sanctions": { "error": "401 Client Error: Unauthorized for url: ..." }
```

**The fix** was to send an authentication header and use the correct endpoint:

```python
# BEFORE (no auth):
r = requests.post(f"{OS_BASE}/match/default", json=payload, params={"algorithm": "best"})

# AFTER (with the API key in a header):
headers = {"Authorization": f"ApiKey {os_key}"}
r = requests.post(f"{OS_BASE}/match/default", json=payload, headers=headers,
                  params={"algorithm": "best"})
```

**Layer B — The key was read too early (a subtle ordering bug).** Even after
adding the key to our `.env` file, we *still* got "No API key set". Why?

Our tool file read the key at the very top, the moment it was imported:

```python
# tools.py  (the buggy version)
OS_KEY = os.getenv("OPENSANCTIONS_API_KEY", "")   # ← runs at IMPORT time
```

But the `.env` file (which holds the key) was loaded *later*, in `agent.py`:

```python
# agent.py
from tools import ...     # ← line A: this imports tools.py → OS_KEY is read here, too early!
load_dotenv()             # ← line B: the key only becomes available HERE, too late
```

So `OS_KEY` was captured as empty **before** the key was ever loaded.

**The fix:** read the key *inside the function*, at the moment it's actually
needed (by which time `.env` is loaded):

```python
def screen_sanctions(name: str, country: str = "") -> dict:
    os_key = os.getenv("OPENSANCTIONS_API_KEY", "")   # ← read at CALL time, not import time
    if not os_key:
        return {"name": name, "match": None, "error": "No OPENSANCTIONS_API_KEY set..."}
    ...
```

**Lesson:** *When* you read a value matters as much as *what* you read. Reading
configuration at import time, before it's loaded, is a classic silent bug.

---

### 🐛 Bug #4 — The biggest one: it blocked a perfectly good bank

This is the most important lesson in the whole project.

**What happened:** Once sanctions screening worked, we tested it with
**"JP Morgan Chase"** — a famous, legitimate US bank. The agent **BLOCKED** it:

```json
{
  "decision": "BLOCK",
  "rationale": "confident sanctions match with a score of 0.99",
  "evidence": { "sanctions": { "match_level": "confident", "score": 0.99,
                               "matched_entity": "JPMorgan Chase" } }
}
```

That's clearly wrong. JP Morgan is not sanctioned. What went wrong?

**Why:** We assumed a **high name-match score = sanctioned**. But that's false.
The OpenSanctions database is **not** only a list of banned companies. It
aggregates *hundreds* of different lists:

- 🚫 actual **sanctions** lists (the banned ones)
- 🏛️ **PEP** lists (politically exposed persons — politicians, etc.)
- ⚖️ **regulatory actions** (fines, enforcement records)
- 🏢 company registries, news mentions, and more

JP Morgan appears in there because it has *regulatory records* — **not** because
it's sanctioned. Our code saw a 99% name match and blindly blocked it. It was
checking *"do the names match?"* but never *"match to **what kind of** entry?"*

**The first (too-simple) version of the code:**

```python
# Only looked at the score — ignored WHAT the entity was flagged for
return {
    "name": name,
    "match": score >= 0.70,
    "match_level": "confident" if score >= 0.85 else "fuzzy",
    "score": score,
}
```

**The fix:** Every match carries a `topics` field — tags that say *what kind of
risk* it is (`sanction`, `role.pep`, `reg.action`, etc.). We now read those
topics and only treat a match as a real ban if it actually carries a
**sanction** topic:

```python
topics = top.get("properties", {}).get("topics", [])

# A high name score ALONE is not a sanctions hit. Check WHAT kind of entry matched.
is_sanctioned = any(t in ("sanction", "sanction.linked") for t in topics)
is_other_risk = bool(topics) and not is_sanctioned

if is_sanctioned and score >= 0.85:
    match_level = "confident_sanction"   # → BLOCK
elif is_sanctioned and score >= 0.70:
    match_level = "fuzzy_sanction"       # → REVIEW (possible false positive)
elif is_other_risk and score >= 0.70:
    match_level = "other_risk"           # → REVIEW (PEP/regulatory, NOT a ban)
else:
    match_level = "none"                 # → clean
```

**The result after the fix:**

| Company | Before | After | Why |
|---|---|---|---|
| JP Morgan Chase | ⛔ BLOCK (wrong) | ✅ ALLOW | No sanction topic — just a clean name match |
| Bright Future Trading | ⛔ BLOCK | ⚠️ REVIEW | Matched a *regulatory action*, not a sanction |
| Pars Petrochemical | ⛔ BLOCK | ⛔ BLOCK | Genuinely carries a `sanction` topic |

**Lesson — and this is the heart of the project:** A name match is not a
decision. Real screening asks *what kind of risk* an entity carries. We moved
from naive **name-matching** to proper **risk-based screening** — which is the
actual difference between a toy and a real compliance tool.

---

### 🐛 Bug #5 — We let the language model do the math (and it got it wrong)

**What happened:** We tested a payment of ₹800,000 to a clean company in India.
₹800,000 is about **$8,400** — comfortably *under* the $10,000 threshold, so it
should be ALLOWED. But the agent returned REVIEW, with this rationale:

```
"The payment amount exceeds the USD 10,000 threshold..."
```

The evidence showed `amount_usd: 9800` — which is **below** 10,000. The agent
literally contradicted its own evidence. It *said* "exceeds 10,000" while
looking at a number under 10,000.

**Why:** We were asking the **language model** to compare the numbers itself
(*"is $9,800 ≥ $10,000?"*). Language models predict text — they are **unreliable
at arithmetic and comparisons**. It saw a big-looking number and a threshold and
guessed "over" without actually comparing them.

**The fix:** Take the math out of the model's hands. The **code** does the
comparison and hands the model a simple true/false flag it cannot misread:

```python
# In get_fx_rate — the CODE computes this, not the LLM:
"over_threshold": round(amount_usd, 2) >= EDD_THRESHOLD_USD,
```

And the agent's instructions changed from "compare the amount" to "just read the
flag":

```
- get_fx_rate returns an "over_threshold" boolean (the code already did the
  math — do NOT compare the numbers yourself).
```

**Lesson — one of the most important in all of LLM engineering:** *Never make
the language model the calculator.* Any decision that hinges on a number — a
threshold, a count, a date — should be computed in code. The model's job is to
**orchestrate and explain**, not to **calculate**.

---

### 🐛 Bug #6 — A dead API that failed *silently* and returned a believable lie

**What happened:** Even after Bug #5, the same payment was *still* going to
REVIEW. We tested the currency tool directly (with no language model involved)
and found the smoking gun:

```
INPUT : { amount: 800000, currency: 'INR' }
OUTPUT: { amount_usd: 0, rate: null, over_threshold: false }
```

The conversion returned **$0**. ₹800,000 is not $0. The tool wasn't converting
at all.

**Why:** The currency API we were using (`exchangerate.host`) had **changed its
rules** — it now requires a paid access key (just like the sanctions API did
earlier). Our request silently failed, returned no value, and our code treated
the missing value as **0**. The worst kind of bug: it didn't crash, it returned
a *plausible-looking wrong answer*.

**The fix — two parts:**

1. **Switch to a working keyless API** (`open.er-api.com`, free, no key needed):

```python
r = requests.get(f"https://open.er-api.com/v6/latest/{ccy}", timeout=15)
usd_rate = r.json().get("rates", {}).get("USD")
amount_usd = amount * usd_rate
```

2. **Fail loudly, never silently.** If the conversion can't happen, return an
   explicit error instead of a misleading 0:

```python
if not usd_rate:
    return {"currency": ccy, "error": f"No USD rate available for {ccy}"}
```

After the fix, the same input returns the truth:
```
OUTPUT: { amount_usd: 8471.20, rate: 0.010589, over_threshold: false }   ✅
```

**Lesson:** External services change underneath you, and **the dangerous
failures are the silent ones**. A tool that returns `$0` looks like it worked.
Always make tools fail *loudly* (with a clear error) rather than returning a
default value that can masquerade as a real answer. This was the **third** API
in this project to start requiring a key — a real lesson in not over-trusting
free external services.

---

## 8. Example outputs

These are **real outputs** from the finished agent (screened against live data):

**✅ ALLOW** — a clean payment to a legitimate bank:
```json
{
  "decision": "ALLOW",
  "rationale": "Amount below the USD 10,000 threshold, not a high-risk
                jurisdiction, and sanctions screening returned no matches.",
  "evidence": { "sanctions": { "match_level": "none", "topics": [] },
                "fx": { "amount_usd": 8000 } }
}
```

**⚠️ REVIEW** — a counterparty with a regulatory record (not a ban):
```json
{
  "decision": "REVIEW",
  "rationale": "Matched a 'reg.action' entry (a regulatory enforcement record),
                which requires human review rather than an automatic block.",
  "evidence": { "sanctions": { "match_level": "other_risk", "score": 0.74,
                               "topics": ["reg.action"],
                               "lists": ["us_cftc_enforcement_actions"] } }
}
```

**⛔ BLOCK** — a genuinely sanctioned entity:
```json
{
  "decision": "BLOCK",
  "rationale": "Confident sanctions match (score 0.924) carrying 'sanction',
                'export.control', and 'debarment' topics.",
  "evidence": { "sanctions": { "match_level": "confident_sanction", "score": 0.924,
                               "matched_entity": "Pars Petrochemical Company",
                               "topics": ["sanction", "export.control", "debarment"] } }
}
```

> Note: because this screens **live** data, results can change as the underlying
> sanctions and regulatory lists are updated over time.

---

## 9. How to run it yourself

**Step 1 — Install (one time):**
```bash
python -m venv .venv
# Windows:        .venv\Scripts\Activate.ps1
# Mac/Linux:      source .venv/bin/activate
pip install -r requirements.txt
```

**Step 2 — Add your free API keys.** Copy `.env.example` to `.env` and fill in:
- `GROQ_API_KEY` — free at https://console.groq.com (powers the language model)
- `OPENSANCTIONS_API_KEY` — free at https://www.opensanctions.org/api (live sanctions)

**Step 3 — Build the searchable rulebook (one time):**
```bash
python src/ingest.py
```

**Step 4 — Run it. Two ways:**

*As a script (prints demo results to your terminal):*
```bash
python src/agent.py
```

*As a web service (test your own inputs in a browser):*
```bash
uvicorn api:app --reload --app-dir src
```
Then open **http://127.0.0.1:8000/docs**, click `POST /screen` → "Try it out",
edit the fields, and click "Execute".

---

## 10. Important honesty notes & limitations

This project is a **learning demo**, and being honest about its limits is part
of doing this well:

- **A note on how currency is handled.** The `get_fx_rate` tool converts the
  payment amount into USD before checking it against the policy's USD threshold.
  The currency is taken **from the request as stated** (e.g. "INR 800000" →
  INR). If a request gives an amount with **no currency**, the tool treats it as
  **USD by default** — it does *not* guess the currency from the destination
  country. This is deliberate: a company can legitimately send USD to any
  country, so inferring currency from geography would be wrong. Always state the
  currency explicitly in a request.

- **⚠️ This is NOT a certified compliance system.** Real AML systems need
  audited data sources, model governance, full audit trails, and human
  oversight. This demonstrates the *pattern*, not a production-ready product.
- **The policy documents are synthetic** — written for this demo, modeled on the
  *structure* of real US AML regulation (OFAC, FinCEN, the Bank Secrecy Act),
  but not the real policy of any real institution. Never claim otherwise.
- **The live data is real**, however — OpenSanctions aggregates actual
  government sanctions lists, and the exchange rates are live market rates.
- **The thresholds (0.85 / 0.70) are reasonable defaults, not tuned values.** In
  a real system you'd calibrate them against labeled historical data to balance
  catching real hits against drowning analysts in false positives.

---

## 11. Tech stack

**Python** · **FastAPI** (web service) · **Docker** (packaging) ·
**Groq / Llama 3.3 70B** (the language model) · **ChromaDB** (vector search for
RAG) · **sentence-transformers** (turns text into searchable vectors) ·
**OpenSanctions API** (live sanctions data) · **exchangerate.host** (live FX).

---

*Built as a portfolio project to demonstrate RAG + tool-calling agent design,
live API integration, and — just as importantly — the ability to find and fix
real bugs in agent logic.*