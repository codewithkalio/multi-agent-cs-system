# Multi-Agent Customer Support System with MCP & A2A



## 🎯 Goal
Build my own multi-agent system using ADK 



## 📦 What exists

- Supabase “phase 1” for a customer support demo:
  - `customers`, `orders`, `support_tickets` tables
  - UUID primary/foreign keys, RLS enabled
  - Seeded demo rows (10+ per table)
- An ADK-based support router in `support_agent/agent.py`:
  - Uses an MCP Supabase toolset to answer billing/order questions
  - Routes requests to a billing specialist agent

## 🛠️ What will be built next

- Returns/refunds flow:
  - New ADK specialists
  - Separate Returns service: `check_return_eligibility` + `initiate_return`
  - A2A wiring via `to_a2a()` / `RemoteA2aAgent`
- Connect + end-to-end test with the Dev UI scenarios.

