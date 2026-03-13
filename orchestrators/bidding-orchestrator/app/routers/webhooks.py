from fastapi import APIRouter, HTTPException, Request

from app.schemas.requests import WebhookResponse

router = APIRouter()


@router.post(
    "/api/webhooks/stripe",
    response_model=WebhookResponse,
    tags=["Webhook"],
    summary="Handle Stripe webhook events",
    description="Verifies Stripe signature, parses event, starts WalletTopUpWorkflow for completed checkout sessions.",
)
async def handle_stripe_webhook(request: Request):
    """
    Handle Stripe webhook → start WalletTopUpWorkflow.

    Steps:
    1. Verify Stripe signature using STRIPE_WEBHOOK_SECRET
    2. Parse event payload
    3. If checkout.session.completed with type=wallet_topup:
       Start WalletTopUpWorkflow via Temporal client (idempotent workflow ID)

    See BUILD_INSTRUCTIONS_V2.md Section 9 — Stripe Webhook Handler
    """
    # TODO: Implement
    raise HTTPException(501, "Not implemented yet")
