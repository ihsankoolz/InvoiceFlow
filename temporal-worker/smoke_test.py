"""
Smoke test: manually starts a LoanMaturityWorkflow against the local Temporal server.
Run from temporal-worker/ with: python smoke_test.py

Requires: pip install temporalio
Requires: docker compose up -d (Temporal must be running on localhost:7233)
"""

import asyncio
from datetime import datetime, timezone, timedelta

from temporalio.client import Client


async def main():
    client = await Client.connect("localhost:7233")

    # Due date 30 seconds from now so the first sleep is short
    due_date = (datetime.now(timezone.utc) + timedelta(seconds=30)).isoformat()
    loan_id = "smoke-loan-001"

    print(f"Starting LoanMaturityWorkflow: loan_id={loan_id}, due_date={due_date}")

    handle = await client.start_workflow(
        "LoanMaturityWorkflow",
        args=[loan_id, due_date],
        id=f"smoke-{loan_id}",
        task_queue="invoiceflow-queue",
    )

    print(f"Workflow started: {handle.id}")
    print(f"Track it at: http://localhost:8088/namespaces/default/workflows/{handle.id}")
    print()
    print("Waiting for result (this will take ~REPAYMENT_WINDOW_SECONDS after due_date)...")

    try:
        result = await handle.result()
        print(f"Workflow completed: {result}")
    except Exception as e:
        cause = e
        while hasattr(cause, '__cause__') and cause.__cause__:
            cause = cause.__cause__
        print(f"Workflow FAILED: {type(cause).__name__}: {cause}")


if __name__ == "__main__":
    asyncio.run(main())
