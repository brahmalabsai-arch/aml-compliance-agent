# Project Walkthrough — How This Agent Works

A plain-language tour of every file, the data flow, the chunking strategy, and
how to see each part working. Read this top to bottom and you'll be able to
explain the whole project in an interview.

---

## The one-sentence summary

A user asks *"can we pay company X in country Y?"* — the agent looks up the
relevant **policy rule** (RAG), checks **live sanctions + exchange-rate data**
(API tools), and returns an **ALLOW / REVIEW / BLOCK** verdict with its reasoning.

---

## The big picture: two kinds of knowledge

Every compliance decision needs two things that live in different places:

| Knowledge | Example | Changes? | Where it lives | How we access it |
|---|---|---|---|---|
| **The rule** | "Never pay a sanctioned entity" | Rarely | A policy document | **RAG** (vector search) |
| **The live fact** | "Is X sanctioned *today*?" | Daily | An external service | **API call** (a tool) |

You can't bake a daily-changing sanctions list into a document, so the agent
fetches it live. The whole project exists to *tie these two together*.

---

## File-by-file

### `data/aml_policy.md` and `data/kyc_standard.md` — the knowledge base
These are your **RAG corpus** — the rulebook the agent searches. Plain markdown
policy documents, written in numbered sections (Section 1, Section 2...).

**Are these real?** No — they are **synthetic** documents written for this demo,
modeled on the real *structure* of US AML/KYC regulation. The vocabulary is
authentic (OFAC SDN, SAR filing, EDD, FATF, the $10,000 BSA-style threshold) but
the specific institution ("Meridian Pay Inc.") and document are invented.
Companies don't publish their internal AML policies, so a synthetic-but-realistic
corpus is the correct and honest choice for a portfolio project. **Never claim
these are a real institution's policy.**

**What IS real:** the *live tools* hit real data — OpenSanctions aggregates
actual OFAC/EU/UN/UK sanctions lists, and the FX rates are real market rates.
So the split is: synthetic policy corpus + real live data sources.

**This is component #1 of your project: the RAG documents.**

### `src/ingest.py` — turns documents into a searchable store
Run **once** before anything else. It:
1. Reads every `.md` file in `data/`.
2. **Chunks** each document into sections (see "Chunking" below).
3. Converts each chunk into a vector (an embedding) using the
   `all-MiniLM-L6-v2` model.
4. Stores the vectors in ChromaDB (the `chroma_db/` folder).

After this runs, you have a searchable knowledge base. Think of it as building
the index of a book so you can later look things up by meaning, not keywords.

### `src/tools.py` — the three things the agent can *do*
This is the heart of "tool-calling." It defines three tools plus their schemas
(the descriptions the LLM reads to decide when to use each):

1. **`rag_search(query)`** — searches the ChromaDB store and returns the most
   relevant policy clauses. *This is how the agent reads the rulebook.*
2. **`screen_sanctions(name, country)`** — calls the live **OpenSanctions API**
   to check if a counterparty is on a sanctions list. *Live data #1.*
3. **`get_fx_rate(amount, currency, country)`** — calls the live
   **exchangerate.host API** to convert the payment amount **into USD**, so it
   can be checked against the policy's USD thresholds (the $10,000 EDD line).
   *Live data #2 — the supporting tool, not the star.*
   **This is component #2 of your project: the online data API.**

Each tool returns a plain dictionary so it can be cleanly converted to JSON and
handed back to the LLM.

### `src/agent.py` — the brain / the loop
This orchestrates everything. The flow:
1. Sends the user's question + the tool descriptions to the LLM (Groq, Llama 3.3).
2. The LLM decides *which* tools to call and with what arguments.
3. The code executes those tools and feeds the results back to the LLM.
4. The LLM repeats if it needs more info, then returns a final **JSON verdict**.

The key idea: **you don't hard-code the logic.** You give the LLM tools and a
policy, and it figures out the sequence — look up the rule, screen the name,
check the amount, then decide. That's what makes it an *agent* rather than a
script with if-statements.

### `src/api.py` — the web door (FastAPI)
Wraps `agent.run()` in an HTTP endpoint so other programs can use it over the
network. Exposes:
- `GET /health` — a simple "is it alive?" check.
- `POST /screen` — send a transaction, get back a verdict.
- `GET /docs` — an auto-generated, browsable testing page (FastAPI gives this
  for free).

The agent logic doesn't change at all — this just puts a web interface on it.

### `src/inspect_store.py` — your debugging window
A helper (not part of the agent) that lets you **see inside the vector store**:
- `python src/inspect_store.py` lists every stored chunk.
- `python src/inspect_store.py "a question"` shows what gets retrieved for it.
Use this to verify your RAG is working without going through the web app.

### `Dockerfile` — packages the whole thing
Bundles Python, all dependencies, and the pre-built vector store into one
container that runs identically anywhere. See `DOCKER_GUIDE.md`.

### `tests/test_tools.py` — basic sanity checks
Verifies the tools return the expected shapes.

---

## Chunking — the strategy and why

**What is a chunk?** Before a document can be searched by meaning, it's split
into smaller pieces ("chunks"). Each chunk becomes one searchable unit. When you
ask a question, the system finds the chunks closest in meaning to your question.

**The strategy used here: section-based (structure-aware) chunking.**
In `ingest.py`, the `chunk_by_section` function splits each document at every
`## Section` heading. So **one chunk = one complete policy section.**

Your store holds **9 chunks total**: 6 from `aml_policy.md`, 3 from
`kyc_standard.md`.

**Why this strategy (and not the alternatives):**

| Strategy | How it splits | Problem for policy docs |
|---|---|---|
| Fixed-size | Every N characters | Cuts a rule in half mid-sentence |
| Recursive | By paragraphs/sentences to a size cap | Can still split related clauses |
| **Section-based (ours)** | At document headings | Keeps each rule whole ✓ |

Policy clauses are self-contained units of meaning. "Section 3 — Sanctions
Screening" is one complete thought. Splitting it would return fragments with no
context. Section-based chunking keeps each retrievable unit semantically whole —
a deliberate choice that fits *this* data. (For a 500-page book you'd choose
differently; chunking strategy always depends on the document structure.)

**To see the chunks yourself:** `python src/inspect_store.py`

---

## The full data flow (one request, start to finish)

```
1. You POST: {"name": "Pars Petrochemical", "country": "Iran", "amount_usd": 50000}
                          │
2. api.py turns it into a question and calls agent.run()
                          │
3. agent.py sends question + tool list to the LLM
                          │
4. LLM: "I should call rag_search('sanctioned entity policy')"
                          │
5. rag_search hits ChromaDB → returns Section 3: "never transact with
   sanctioned entities → BLOCK"
                          │
6. LLM: "Now call screen_sanctions('Pars Petrochemical', 'Iran')"
                          │
7. screen_sanctions hits OpenSanctions API → returns a match
                          │
8. LLM reasons: rule says block sanctioned entities (RAG) + this entity
   matched (API) → decision = BLOCK
                          │
9. Returns JSON: {"decision": "BLOCK", "rationale": "...", "clauses": [...]}
```

That cross-check in step 8 — *"the rule says X, the live data says Y, therefore
Z"* — is exactly what a human compliance analyst does manually. You've automated
the lookup and the cross-check.

---

## How to see each part working (no web app needed)

| What you want to see | Command |
|---|---|
| All the chunks in your store | `python src/inspect_store.py` |
| What gets retrieved for a question | `python src/inspect_store.py "pay a sanctioned firm"` |
| The full agent making decisions | `python src/agent.py` |
| The API + browsable test page | `uvicorn api:app --app-dir src` then open `/docs` |
| Everything in a container | see `DOCKER_GUIDE.md` |
