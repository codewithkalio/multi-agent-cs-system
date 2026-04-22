"""
eval.py — Automated evaluation for the multi-agent customer support system.

Uses LLM-as-judge to score agent responses against expected behavior.
Traces every eval run in LangFuse: agent calls, LLM judge generations,
and per-test-case scores are all visible in the LangFuse dashboard.

Add new test cases by appending to the TEST_CASES list.

Usage:
    # Terminal 1: start the returns agent
    python returns_agent.py

    # Terminal 2: run the eval
    python eval.py
"""

import asyncio
import json
import os
import sys
from dataclasses import dataclass
import warnings

from dotenv import load_dotenv
from google.adk.agents import Agent
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

# LangFuse 4.x imports
# observe: decorator that wraps any function as a LangFuse span/trace
# get_client: returns the global LangFuse client for scoring and flushing
from langfuse import observe, get_client

# Drop-in OpenAI replacement: every call is captured as a LangFuse Generation automatically
from langfuse.openai import OpenAI

warnings.filterwarnings("ignore")
load_dotenv()

# The LangFuse client reads LANGFUSE_PUBLIC_KEY, LANGFUSE_SECRET_KEY,
# and LANGFUSE_HOST from environment variables automatically.
_langfuse = get_client()


# ---------------------------------------------------------------------------
# Test cases — add new dicts here to scale the eval
# ---------------------------------------------------------------------------

TEST_CASES = [
    {
        "id": "billing_order_status",
        "description": "Billing agent looks up a real order from Supabase",
        "message": "What is the status of order ORD-2025-0001?",
        "criteria": (
            "The response should route to billing_agent and return a real order status "
            "such as pending, delivered, or shipped. It should not say it has no access to data."
        ),
    },
    {
        "id": "billing_customer_lookup",
        "description": "Billing agent looks up customer information",
        "message": "Can you look up orders for customer email kira.nakamura@example.com?",
        "criteria": (
            "The response should query the database. If no customer is found it should "
            "say so clearly. It should not say it cannot access customer data."
        ),
    },
    {
        "id": "return_initiation",
        "description": "Returns agent initiates a return via A2A",
        "message": "I want to return order ORD-2025-0002. It doesn't fit.",
        "criteria": (
            "The response should confirm the return has been initiated and provide a return ID. "
            "It should mention a shipping label will be sent."
        ),
    },
    {
        "id": "return_eligibility_check",
        "description": "Returns agent checks eligibility before initiating",
        "message": "Is order ORD-2025-0003 eligible for a return?",
        "criteria": (
            "The response should check return eligibility and clearly state whether "
            "the order is eligible, including the return window information."
        ),
    },
    {
        "id": "escalation_human_request",
        "description": "Escalation agent handles request for human support",
        "message": "I'm extremely frustrated and I need to speak to a real human right now.",
        "criteria": (
            "The response should empathize with the customer, confirm a human agent will follow up, "
            "and ask for the customer's email address. It should not try to resolve the issue itself."
        ),
    },
    {
        "id": "escalation_complex_complaint",
        "description": "Escalation agent handles unresolved complaints",
        "message": "I've been charged twice for my order and nobody has helped me. This is unacceptable.",
        "criteria": (
            "The response should acknowledge the frustration, escalate to a human, "
            "and ask for the customer's email. It should not attempt to process a refund directly."
        ),
    },
    {
        "id": "routing_accuracy",
        "description": "Root agent delegates order queries to billing_agent",
        "message": "What are my recent orders?",
        "criteria": (
            "The response should return real order data from the database. "
            "It is acceptable for the root agent to present the results."
        ),
    },
]


# ---------------------------------------------------------------------------
# Agent runner
# as_type="agent" tags this span as an agent call in the LangFuse UI.
# Input (message) and output (response) are captured automatically.
# ---------------------------------------------------------------------------

@observe(name="agent_run", as_type="agent")
async def run_agent(agent, message: str, session_service, app_name: str) -> str:
    """Run an ADK agent and return the final response."""
    runner = Runner(agent=agent, app_name=app_name, session_service=session_service)
    session = await session_service.create_session(app_name=app_name, user_id="eval_user")
    content = types.Content(role="user", parts=[types.Part(text=message)])

    response = "(no response)"
    async for event in runner.run_async(
        user_id="eval_user",
        session_id=session.id,
        new_message=content,
    ):
        if event.is_final_response() and event.content and event.content.parts:
            response = event.content.parts[0].text

    return response


# ---------------------------------------------------------------------------
# LLM judge
# as_type="evaluator" tags this span correctly in LangFuse.
# The OpenAI call inside is captured automatically as a nested Generation
# because we imported OpenAI from langfuse.openai (drop-in wrapper).
# ---------------------------------------------------------------------------

@observe(name="llm_judge", as_type="evaluator")
def judge_response(test_case: dict, agent_response: str) -> dict:
    """Use OpenAI to judge whether the agent response meets the criteria."""
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    prompt = f"""You are evaluating an AI customer support agent's response.

Test case: {test_case['description']}
User message: {test_case['message']}
Success criteria: {test_case['criteria']}

Agent response:
{agent_response}

Evaluate whether the agent response meets the success criteria.
Respond ONLY with a valid JSON object in this exact format:
{{
  "pass": true or false,
  "score": 0.0 to 1.0,
  "reason": "one sentence explanation"
}}"""

    result = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_object"},
    )
    return json.loads(result.choices[0].message.content)


# ---------------------------------------------------------------------------
# Per-test-case runner
# Each call becomes one root Trace in LangFuse containing:
#   - agent_run span (the ADK multi-agent call)
#   - llm_judge span with a nested Generation (the OpenAI judge call)
#   - a numeric score attached to the trace
# ---------------------------------------------------------------------------

@observe(name="eval_test_case")
async def run_test_case(test_case: dict, agent, session_service) -> tuple[str, dict]:
    """Run one test case, judge it, and attach the score to the LangFuse trace."""
    _langfuse.update_current_span(
        metadata={
            "test_id": test_case["id"],
            "description": test_case["description"],
            "criteria": test_case["criteria"],
        }
    )

    response = await run_agent(
        agent,
        test_case["message"],
        session_service,
        app_name=f"eval_{test_case['id']}",
    )

    judgment = judge_response(test_case, response)

    # Attach the numeric score to this trace — visible in the LangFuse dashboard
    # alongside the full conversation, token counts, and latency
    _langfuse.score_current_trace(
        name="eval_score",
        value=judgment["score"],
        data_type="NUMERIC",
        comment=judgment["reason"],
    )

    return response, judgment


# ---------------------------------------------------------------------------
# Main eval runner
# ---------------------------------------------------------------------------

@dataclass
class EvalResult:
    test_id: str
    description: str
    passed: bool
    score: float
    reason: str
    agent_response: str


async def run_eval():
    """Run all test cases and print a summary report."""

    # Import here to avoid circular issues with ADK module loading
    sys.path.insert(0, ".")
    from support_agent.agent import root_agent

    session_service = InMemorySessionService()
    results: list[EvalResult] = []

    print("\n" + "=" * 60)
    print("  MULTI-AGENT CUSTOMER SUPPORT — EVAL REPORT")
    print("=" * 60)

    for i, test_case in enumerate(TEST_CASES, 1):
        print(f"\n[{i}/{len(TEST_CASES)}] {test_case['id']}")
        print(f"  Message: {test_case['message'][:60]}...")

        try:
            response, judgment = await run_test_case(
                test_case,
                root_agent,
                session_service,
            )

            result = EvalResult(
                test_id=test_case["id"],
                description=test_case["description"],
                passed=judgment["pass"],
                score=judgment["score"],
                reason=judgment["reason"],
                agent_response=response,
            )
        except Exception as e:
            result = EvalResult(
                test_id=test_case["id"],
                description=test_case["description"],
                passed=False,
                score=0.0,
                reason=f"Error: {e}",
                agent_response="",
            )

        results.append(result)
        status = "✅ PASS" if result.passed else "❌ FAIL"
        print(f"  {status}  (score: {result.score:.1f}) — {result.reason}")

    # Summary
    passed = sum(1 for r in results if r.passed)
    total = len(results)
    avg_score = sum(r.score for r in results) / total

    print("\n" + "=" * 60)
    print(f"  RESULTS: {passed}/{total} passed  |  avg score: {avg_score:.2f}")
    print("=" * 60)

    # Failures detail
    failures = [r for r in results if not r.passed]
    if failures:
        print("\n📋 FAILURES:")
        for r in failures:
            print(f"\n  [{r.test_id}]")
            print(f"  Reason: {r.reason}")
            print(f"  Response: {r.agent_response[:200]}...")

    print()

    # Flush all buffered LangFuse events before the process exits.
    # LangFuse batches events for efficiency — without this call, the last
    # traces in a short-lived script may not be sent.
    _langfuse.flush()

    return passed == total


if __name__ == "__main__":
    success = asyncio.run(run_eval())
    sys.exit(0 if success else 1)
