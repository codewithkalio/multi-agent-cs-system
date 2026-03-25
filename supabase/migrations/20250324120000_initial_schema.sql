-- Phase 1: customers, orders, support_tickets with UUID PKs/FKs and RLS.
-- Service role bypasses RLS; anon/authenticated need policies below for MCP/agents using those keys.

-- ---------------------------------------------------------------------------
-- Tables
-- ---------------------------------------------------------------------------

CREATE TABLE public.customers (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  email text NOT NULL UNIQUE,
  full_name text NOT NULL,
  phone text,
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE public.orders (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  customer_id uuid NOT NULL REFERENCES public.customers (id) ON DELETE CASCADE,
  order_number text NOT NULL UNIQUE,
  status text NOT NULL DEFAULT 'pending'
    CHECK (status IN ('pending', 'processing', 'shipped', 'delivered', 'cancelled')),
  total_cents integer NOT NULL CHECK (total_cents >= 0),
  currency text NOT NULL DEFAULT 'USD',
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX orders_customer_id_idx ON public.orders (customer_id);
CREATE INDEX orders_status_idx ON public.orders (status);

CREATE TABLE public.support_tickets (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  customer_id uuid NOT NULL REFERENCES public.customers (id) ON DELETE CASCADE,
  order_id uuid REFERENCES public.orders (id) ON DELETE SET NULL,
  subject text NOT NULL,
  body text,
  status text NOT NULL DEFAULT 'open'
    CHECK (status IN ('open', 'in_progress', 'resolved', 'closed')),
  priority text NOT NULL DEFAULT 'normal'
    CHECK (priority IN ('low', 'normal', 'high', 'urgent')),
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX support_tickets_customer_id_idx ON public.support_tickets (customer_id);
CREATE INDEX support_tickets_order_id_idx ON public.support_tickets (order_id);
CREATE INDEX support_tickets_status_idx ON public.support_tickets (status);

-- ---------------------------------------------------------------------------
-- Row Level Security
-- ---------------------------------------------------------------------------

ALTER TABLE public.customers ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.orders ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.support_tickets ENABLE ROW LEVEL SECURITY;

-- Demo / course: allow anon + authenticated clients full access when using the public API key.
-- Replace with stricter policies in production.

CREATE POLICY "customers_all_anon" ON public.customers
  FOR ALL TO anon
  USING (true)
  WITH CHECK (true);

CREATE POLICY "customers_all_authenticated" ON public.customers
  FOR ALL TO authenticated
  USING (true)
  WITH CHECK (true);

CREATE POLICY "orders_all_anon" ON public.orders
  FOR ALL TO anon
  USING (true)
  WITH CHECK (true);

CREATE POLICY "orders_all_authenticated" ON public.orders
  FOR ALL TO authenticated
  USING (true)
  WITH CHECK (true);

CREATE POLICY "support_tickets_all_anon" ON public.support_tickets
  FOR ALL TO anon
  USING (true)
  WITH CHECK (true);

CREATE POLICY "support_tickets_all_authenticated" ON public.support_tickets
  FOR ALL TO authenticated
  USING (true)
  WITH CHECK (true);
