"""Optional local inference budget shared by API and worker processes."""
from alembic import op

revision = "0010_test_budget"
down_revision = "0009_search_readiness"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""CREATE TABLE inference_budget_runs (
        id text PRIMARY KEY, limit_usd numeric(20,10) NOT NULL CHECK(limit_usd>0),
        spent_usd numeric(20,10) NOT NULL DEFAULT 0, reserved_usd numeric(20,10) NOT NULL DEFAULT 0,
        paused boolean NOT NULL DEFAULT false, created_at timestamptz NOT NULL DEFAULT now())""")
    op.execute("""CREATE TABLE inference_budget_calls (
        id uuid PRIMARY KEY, run_id text NOT NULL REFERENCES inference_budget_runs(id),
        model text NOT NULL, operation text NOT NULL, input_bound integer NOT NULL, output_bound integer NOT NULL,
        reserved_usd numeric(20,10) NOT NULL, actual_usd numeric(20,10),
        status text NOT NULL CHECK(status IN ('reserved','settled','unknown')),
        created_at timestamptz NOT NULL DEFAULT now())""")


def downgrade():
    op.execute("DROP TABLE inference_budget_calls")
    op.execute("DROP TABLE inference_budget_runs")
