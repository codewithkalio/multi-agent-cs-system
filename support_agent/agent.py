from google.adk.agents.llm_agent import Agent

billing_agent = Agent(
    model='gemini-2.5-flash',
    name='billing_agent',
    description='Handles customer billing and order questions.',
    instruction='You help customers with billing inquiries and order status. Be concise and helpful.',
)

root_agent = Agent(
    model='gemini-2.5-flash',
    name='root_agent',
    description='Routes customer support requests to the right specialist.',
    instruction="""You are a customer support router. You must ALWAYS delegate to the appropriate sub-agent. Never answer questions yourself.

- Billing, orders, payments, order status → delegate to billing_agent
- Returns or refunds → let the user know that service is coming soon
""",
    sub_agents=[billing_agent],
)
