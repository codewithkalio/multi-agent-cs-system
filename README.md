# Multi-Agent Customer Support System

A multi-agent AI customer support system built with Google ADK. Routes customer inquiries to specialist agents using MCP for database access and A2A for cross-service agent communication.

## 📚 Table of Contents

- [Architecture](#-architecture)
- [Agents](#-agents)
- [Database](#-database)
- [Setup](#-setup)
- [Running the System](#-running-the-system)
- [Manual Test Scenarios](#-manual-test-scenarios)
- [Running Automated Evaluations](#-running-automated-evaluations-evalpy)
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


## 🤖 Agents

**Root Agent** — Routes incoming requests to the appropriate specialist. Never answers directly.

**Billing Agent** — Handles order status, billing, and payment questions. Connects to Supabase via MCP and writes its own SQL queries at runtime.

**Escalation Agent** — Handles complaints and requests for human support. Collects customer email and confirms a 24-hour follow-up.

**Returns Agent** — Runs as a standalone A2A service on port 8001. Checks return eligibility and initiates returns.

## 🗄️ Database

Supabase (Postgres) with three tables:

- `customers` — 10+ customer records
- `orders` — 10+ order records linked to customers
- `support_tickets` — 10+ support ticket records

## ⚙️ Setup

### Prerequisites

- Python 3.10+
- Node.js (for Supabase MCP server via npx)
- A Google Gemini API key
- A Supabase account and project

### Installation

```bash
# Clone the repo
git clone <your-repo-url>
cd multi-agent-cs-system

# Create and activate virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install google-adk python-dotenv uvicorn a2a-sdk

```

### Environment Variables

Create a `.env` file in the project root and inside `support_agent/`:

```
GOOGLE_API_KEY=your_gemini_api_key
SUPABASE_ACCESS_TOKEN=your_supabase_pat
SUPABASE_PROJECT_ID=your_project_ref

```

## 🚀 Running the System

You need two terminals running simultaneously.

**Terminal 1 — Start the Returns Agent (A2A service):**

```bash
source venv/bin/activate
python returns_agent.py

```

The returns agent will be available at `http://localhost:8001`.

**Terminal 2 — Start the main app:**

```bash
source venv/bin/activate
adk web

```

Open `http://localhost:8000` in your browser to access the ADK Dev UI.

## 🧪 Manual Test Scenarios

These are manual prompts you can run in the ADK UI to quickly validate routing and specialist-agent behavior.

**Scenario 1 — Billing via MCP:**

> "What is the status of order ORD-2025-0001?"

The root agent routes to `billing_agent`, which queries Supabase via MCP and returns real order data.

**Scenario 2 — Returns via A2A:**

> "I want to return order ORD-2025-0002."

The root agent routes to `returns_agent` over HTTP via the A2A protocol. The returns service checks eligibility and initiates the return.

**Scenario 3 — Escalation:**

> "I'm really frustrated and need to speak to a human immediately."

The root agent routes to `escalation_agent`, which sympathizes with the customer and collects their email for follow-up.

## 🧾 Running Automated Evaluations

`eval.py` runs an automated evaluation pass against the multi-agent system using predefined test cases.

For each test case, it:

- sends a user message through the root agent
- captures the final agent response
- scores the response with an LLM judge against a success criterion
- prints per-test pass/fail output and a final summary report

### Requirements for eval

- Returns agent running in a separate terminal (`python returns_agent.py`)
- `OPENAI_API_KEY` set in your environment (OpenAI is used to test the Gemini agents)
- Same virtual environment activated

### Run eval and save output to a file

```bash
source venv/bin/activate
python eval.py 2>&1 | tee eval-output.txt

```

This keeps the live output in your terminal and writes the same output to `eval-output.txt`.

## 📁 Project Structure

```
multi-agent-cs-system/
├── support_agent/
│   ├── agent.py          # Root router + billing + escalation agents
│   ├── __init__.py
│   └── .env              # API keys for main app
├── returns_agent.py      # Standalone A2A returns service
├── eval.py               # Automated eval runner + LLM judge scoring
├── eval-output.txt       # Sample saved eval output from tee
├── .env                  # API keys for returns service
├── .gitignore
└── README.md

```

