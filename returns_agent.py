import os
import uvicorn
from dotenv import load_dotenv
from google.adk.agents import Agent
from google.adk.a2a.utils.agent_to_a2a import to_a2a

load_dotenv()

def check_return_eligibility(order_id: str) -> dict:
    """Check if an order is eligible for return."""
    return {
        "order_id": order_id,
        "eligible": True,
        "reason": "Order is within 30-day return window.",
        "return_window_days": 30,
    }

def initiate_return(order_id: str, reason: str) -> dict:
    """Initiate a return for an order."""
    return {
        "return_id": f"RET-{order_id}",
        "order_id": order_id,
        "status": "initiated",
        "message": "Return initiated. You'll receive a shipping label within 24 hours.",
    }

returns_agent = Agent(
    model='gemini-2.5-flash-lite',
    name='returns_agent',
    description='Handles product returns and return eligibility checks.',
    instruction="""You are a returns specialist.
    Use check_return_eligibility to verify if an order can be returned.
    Use initiate_return to start the return process.
    Always check eligibility before initiating a return.""",
    tools=[check_return_eligibility, initiate_return],
)

if __name__ == "__main__":
    app = to_a2a(returns_agent, port=8001)
    uvicorn.run(app, host="0.0.0.0", port=8001)