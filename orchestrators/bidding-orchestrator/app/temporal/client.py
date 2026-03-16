"""
Temporal client for starting workflows and signaling running workflows.
"""

from temporalio.client import Client

from app import config


class TemporalClient:
    """Wraps the Temporal SDK client for starting/signaling workflows."""

    def __init__(self):
        self.client: Client | None = None

    async def connect(self):
        """Connect to Temporal Server at config.TEMPORAL_HOST."""
        self.client = await Client.connect(config.TEMPORAL_HOST)

    async def _get_client(self) -> Client:
        if not self.client:
            await self.connect()
        return self.client

    async def start_workflow(
        self,
        workflow_name: str,
        workflow_id: str,
        args: dict,
        task_queue: str = "invoiceflow-queue",
    ):
        """
        Start a Temporal workflow by string name.

        Args:
            workflow_name: Registered workflow type name (e.g., "WalletTopUpWorkflow")
            workflow_id:   Unique ID — acts as idempotency key (duplicate start is a no-op)
            args:          Single dict argument passed to the workflow run method
            task_queue:    Temporal task queue name
        """
        client = await self._get_client()
        await client.start_workflow(
            workflow_name,
            args=[args],
            id=workflow_id,
            task_queue=task_queue,
        )

    async def signal_workflow(self, workflow_id: str, signal_name: str):
        """
        Signal a running Temporal workflow.

        Used for anti-snipe: sends 'extend_deadline' to the running AuctionCloseWorkflow.
        """
        client = await self._get_client()
        handle = client.get_workflow_handle(workflow_id)
        await handle.signal(signal_name)
