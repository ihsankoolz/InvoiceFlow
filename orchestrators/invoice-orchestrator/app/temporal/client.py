from temporalio.client import Client
from temporalio.exceptions import WorkflowAlreadyStartedError

from app import config


class TemporalClient:
    """Wraps the Temporal SDK client for starting workflows."""

    def __init__(self):
        self.client = None

    async def connect(self):
        """Connect to Temporal Server."""
        if not self.client:
            self.client = await Client.connect(config.TEMPORAL_HOST)
        return self.client

    async def start_workflow(
        self,
        workflow_name: str,
        workflow_id: str,
        args: dict,
        task_queue: str = "invoiceflow-queue",
    ):
        """
        Start a Temporal workflow.

        Args:
            workflow_name: Name of the workflow class (e.g., "AuctionCloseWorkflow")
            workflow_id: Unique ID for this workflow instance (e.g., "auction-{invoice_token}")
            args: Dict of arguments passed positionally to the workflow run method
            task_queue: Temporal task queue name
        """
        if not self.client:
            await self.connect()
        try:
            await self.client.start_workflow(
                workflow_name,
                args=list(args.values()),
                id=workflow_id,
                task_queue=task_queue,
            )
        except WorkflowAlreadyStartedError:
            # Workflow already running for this invoice — safe to ignore.
            # This can happen if the same invoice is submitted twice (e.g. double-click or demo rerun).
            pass
