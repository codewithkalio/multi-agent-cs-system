# Multi-Agent Customer Support System

A multi-agent AI customer support system built with Google ADK. Routes customer inquiries to specialist agents using MCP for database access and A2A for cross-service agent communication. Includes LangFuse observability for tracing, evaluation scoring, and production monitoring.

## 📚 Table of Contents

- [Architecture](#-architecture)
- [Agents](#-agents)
- [Database](#-database)
- [Setup](#-setup)
- [Running the System](#-running-the-system)
- [Manual Test Scenarios](#-manual-test-scenarios)
- [Running Automated Evaluations](#-running-automated-evaluations-evalpy)
- [LangFuse Observability](#-langfuse-observability)
- [Project Structure](#-project-structure)

## 🏗️ Architecture

```
User
  |
  v
Root Agent (router)
  |
  |-- billing_agent -----> MCP -----> Supabase DB
  |                                   (customers, orders, support_tickets)
  |
  |-- escalation_agent (local)
  |
  |-- returns_agent -----> A2A (HTTP :8001) -----> Returns Service
                                                     |-- check_return_eligibility()
                                                     |-- initiate_return()

```


| Layer                | Technology     | Purpose                                  |
| -------------------- | -------------- | ---------------------------------------- |
| Multi-agent routing  | Google ADK     | Root agent delegates to specialists      |
| Database access      | MCP + Supabase | Billing agent queries real customer data |
| Cross-service agents | A2A Protocol   | Returns agent runs as a separate service |
| Observability        | LangFuse       | Traces, eval scores, token costs         |


## 🤖 Agents

**Root Agent** — Routes incoming requests to the appropriate specialist. Never answers directly.

**Billing Agent** — Handles order status, billing, and payment questions. Connects to Supabase via MCP and writes its own SQL queries at runtime.

**Escalation Agent** — Handles complaints and requests for human support. Collects customer email and confirms a 24-hour follow-up.

**Returns Agent** — Runs as a standalone A2A service on port 8001. Checks return eligibility and initiates returns.

## 🗄️ Database

Supabase (Postgres) with three tables:

- `customers` — 10+ customer records
- `orders` — 10+ order records linked to customers
- `support_tickets` — 10+ support ticket records

## ⚙️ Setup

### Prerequisites

- Python 3.10+
- Node.js (for Supabase MCP server via npx)
- A Google Gemini API key
- A Supabase account and project
- A LangFuse account (free at [cloud.langfuse.com](https://cloud.langfuse.com))

### Installation

```bash
# Clone the repo
git clone <your-repo-url>
cd multi-agent-cs-system

# Create and activate virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install google-adk python-dotenv uvicorn a2a-sdk langfuse

```

### Environment Variables

Create a `.env` file in the project root and inside `support_agent/`:

```
GOOGLE_API_KEY=your_gemini_api_key
SUPABASE_ACCESS_TOKEN=your_supabase_pat
SUPABASE_PROJECT_ID=your_project_ref
OPENAI_API_KEY=your_openai_key          # used by eval.py LLM judge

# LangFuse — get these from cloud.langfuse.com → Settings → API Keys
LANGFUSE_PUBLIC_KEY=pk-lf-...
LANGFUSE_SECRET_KEY=sk-lf-...
LANGFUSE_HOST=https://cloud.langfuse.com

```

## 🚀 Running the System

You need two terminals running simultaneously.

**Terminal 1 — Start the Returns Agent (A2A service):**

```bash
source venv/bin/activate
python returns_agent.py

```

The returns agent will be available at `http://localhost:8001`.

**Terminal 2 — Start the main app:**

```bash
source venv/bin/activate
adk web

```

Open `http://localhost:8000` in your browser to access the ADK Dev UI.

## 🧪 Manual Test Scenarios

These are manual prompts you can run in the ADK UI to quickly validate routing and specialist-agent behavior.

**Scenario 1 — Billing via MCP:**

> "What is the status of order ORD-2025-0001?"

The root agent routes to `billing_agent`, which queries Supabase via MCP and returns real order data.

**Scenario 2 — Returns via A2A:**

> "I want to return order ORD-2025-0002."

The root agent routes to `returns_agent` over HTTP via the A2A protocol. The returns service checks eligibility and initiates the return.

**Scenario 3 — Escalation:**

> "I'm really frustrated and need to speak to a human immediately."

The root agent routes to `escalation_agent`, which sympathizes with the customer and collects their email for follow-up.

## 🧾 Running Automated Evaluations

`eval.py` runs an automated evaluation pass against the multi-agent system using predefined test cases.

For each test case, it:

- sends a user message through the root agent
- captures the final agent response
- scores the response with an LLM judge against a success criterion
- prints per-test pass/fail output and a final summary report
- sends a trace and score to LangFuse for every test case

### Requirements for eval

- Returns agent running in a separate terminal (`python returns_agent.py`)
- `OPENAI_API_KEY` set in your environment (OpenAI is used to judge the Gemini agents)
- `LANGFUSE_PUBLIC_KEY` and `LANGFUSE_SECRET_KEY` set in your `.env`
- Same virtual environment activated

### Run eval and save output to a file

```bash
source venv/bin/activate
python eval.py 2>&1 | tee eval-output.txt

```

This keeps the live output in your terminal and writes the same output to `eval-output.txt`.

---

## 📡 LangFuse Observability

[LangFuse](https://langfuse.com) is an open-source LLM engineering platform that gives you full visibility into what your agents are doing — every model call, every routing decision, every token — and lets you attach scores, debug failures, and track quality over time.

### Why observability matters for multi-agent systems

Without observability, multi-agent pipelines are black boxes. When `root_agent` routes to the wrong specialist, or `billing_agent` fails to query Supabase, there's no record of what happened. LangFuse captures everything.

### Core LangFuse concepts

| Concept | What it is | In this project |
|---------|-----------|----------------|
| **Trace** | The top-level unit of work — one request end-to-end | One eval test case run (input → agent → judgment → score) |
| **Span** | A named sub-step within a trace | `agent_run` span (ADK call), `llm_judge` span (scoring step) |
| **Generation** | A span that called an LLM — tracks tokens and cost | GPT-4o-mini judge call, captured automatically |
| **Score** | A numeric or boolean value attached to a trace | `eval_score` (0.0–1.0) from the LLM-as-judge |
| **Session** | Groups related traces (e.g. one user conversation) | Can be added to production runs for multi-turn context |
| **Dataset** | Versioned collection of inputs/expected outputs | `TEST_CASES` in `eval.py` — can be uploaded to LangFuse |

### How it's integrated in `eval.py`

**1. Drop-in OpenAI wrapper** — auto-captures every judge call as a LangFuse Generation:

```python
# Before
from openai import OpenAI

# After — same API, zero config, every call is traced
from langfuse.openai import OpenAI
```

**2. `@observe` decorator** — wraps functions as typed LangFuse spans:

```python
from langfuse import observe, get_client

@observe(name="agent_run", as_type="agent")
async def run_agent(agent, message, session_service, app_name):
    ...  # ADK runner logic — input/output captured automatically

@observe(name="llm_judge", as_type="evaluator")
def judge_response(test_case, agent_response):
    ...  # OpenAI call is auto-traced by the langfuse.openai wrapper
```

**3. Scoring** — attaches the judge's verdict to each trace:

```python
@observe(name="eval_test_case")
async def run_test_case(test_case, agent, session_service):
    response = await run_agent(...)
    judgment = judge_response(test_case, response)

    _langfuse.score_current_trace(
        name="eval_score",
        value=judgment["score"],      # 0.0 to 1.0
        data_type="NUMERIC",
        comment=judgment["reason"],
    )
    return response, judgment
```

**4. Flush before exit** — critical for short-lived scripts:

```python
_langfuse.flush()  # sends all buffered events before the process exits
```

### What you can see in the LangFuse dashboard

After running `eval.py`, open [cloud.langfuse.com](https://cloud.langfuse.com) and navigate to **Traces**:

- **Each test case** appears as a separate trace named `eval:billing_order_status`, `eval:return_initiation`, etc.
- **Nested spans** show the `agent_run` and `llm_judge` steps with their inputs, outputs, and latency
- **Nested Generation** inside `llm_judge` shows the GPT-4o-mini call with exact prompt, response, token counts, and cost
- **Scores** show the numeric `eval_score` next to each trace — you can plot this over time to track quality trends

### Best practices demonstrated

- **`as_type` tagging** — `as_type="agent"` and `as_type="evaluator"` correctly classify spans in the LangFuse UI, making filtering and dashboards more useful
- **Score on the trace, not the span** — `score_current_trace()` attaches the eval result to the top-level trace so it appears in the traces list view, not buried inside a span
- **`flush()` in scripts** — LangFuse batches events for efficiency; without an explicit flush, the last events in a short-lived script can be dropped
- **Metadata for debuggability** — passing `test_id` and `description` as metadata makes it easy to filter by specific test cases in the dashboard

---

## 📁 Project Structure

```
multi-agent-cs-system/
├── support_agent/
│   ├── agent.py          # Root router + billing + escalation agents
│   ├── __init__.py
│   └── .env              # API keys for main app
├── returns_agent.py      # Standalone A2A returns service
├── eval.py               # Automated eval runner + LLM judge + LangFuse tracing
├── eval-output.txt       # Sample saved eval output from tee
├── .env                  # API keys for returns service + LangFuse keys
├── .gitignore
└── README.md

```
