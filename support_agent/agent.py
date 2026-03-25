import os
from dotenv import load_dotenv
from google.adk.agents.llm_agent import Agent
from google.adk.tools.mcp_tool.mcp_toolset import MCPToolset
from google.adk.tools.mcp_tool.mcp_session_manager import StdioConnectionParams
from mcp import StdioServerParameters

load_dotenv()



supabase_mcp = MCPToolset(
    connection_params=StdioConnectionParams(
        server_params=StdioServerParameters(
            command='npx',
            args=[
                '-y',
                '@supabase/mcp-server-supabase@latest',
                '--access-token', os.getenv('SUPABASE_ACCESS_TOKEN'),
                '--project-ref', os.getenv('SUPABASE_PROJECT_ID'),
            ],
        ),
        timeout=30,
    )
)

billing_agent = Agent(
    model='gemini-2.5-flash',
    name='billing_agent',
    description='Handles customer billing and order questions.',
    instruction="""You help customers with billing and order questions.
You have access to a Supabase database with customers, orders, and support_tickets tables.
ALWAYS query the database to answer questions. Never say you don't have access to data.""",
    tools=[supabase_mcp],
)

escalation_agent = Agent(
    model='gemini-2.5-flash',
    name='escalation_agent',
    description='Handles complex issues that need human intervention.',
    instruction="""You handle escalations when other agents cannot resolve a customer's issue.
    Sympathize with the customer, let them know a human support agent will follow up within 24 hours,
    and ask them to confirm their email address so the team can reach them.""",
)

root_agent = Agent(
    model='gemini-2.5-flash',
    name='root_agent',
    description='Routes customer support requests to the right specialist.',
    instruction="""You are a customer support router. You must ALWAYS delegate to the appropriate sub-agent. Never answer questions yourself.

- Billing, orders, payments, order status → delegate to billing_agent
- Returns or refunds → let the user know that service is coming soon
- Complaints, unresolved issues, or requests for a human → delegate to escalation_agent
""",
    sub_agents=[billing_agent, escalation_agent],
)