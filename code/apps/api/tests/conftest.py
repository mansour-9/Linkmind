"""Never run mutation-capable tests in a real MCP/AI preview."""
import os
import pytest

def pytest_sessionstart(session):
    if os.getenv('LINKMIND_TEST_ENVIRONMENT')!='1' or os.getenv('AI_PROVIDER','mock')!='mock' or os.getenv('LINKMIND_CONNECTOR_NETWORK')=='1' or os.getenv('BEDROCK_BUDGET_DATABASE_URL'):
        raise pytest.UsageError('Tests require an explicitly isolated mock environment with external networking and shared inference accounting disabled.')
