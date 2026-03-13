import uuid
from datetime import datetime, timezone
from typing import List

from app.services.email_service import EmailService
from app.services.websocket_manager import ws_manager

# ---------------------------------------------------------------------------
# In-memory notification store (list of dicts matching NotificationResponse)
# ---------------------------------------------------------------------------
notification_store: List[dict] = []

# ---------------------------------------------------------------------------
# Event-to-action mapping
# Each event type maps to a handler config that specifies:
#   - template: email template file name
#   - subject_fn: callable that returns the email subject from the payload
#   - recipients_fn: callable that returns (email_targets, ws_targets) from payload
#     email_targets = list of {"email": str, "user_id": int}
#     ws_targets = list of user_id (int or str)
# ---------------------------------------------------------------------------

EVENT_MAPPING = {
    "invoice.listed": {
        "template": "invoice_listed.html",
        "subject": "Your invoice has been listed",
        "get_recipients": lambda p: (
            [{"email": p.get("seller_email"), "user_id": p.get("seller_id")}],
            [str(p.get("seller_id"))],
        ),
    },
    "invoice.rejected": {
        "template": "invoice_listed.html",
        "subject": "Your invoice has been rejected",
        "get_recipients": lambda p: (
            [{"email": p.get("seller_email"), "user_id": p.get("seller_id")}],
            [str(p.get("seller_id"))],
        ),
    },
    "bid.placed": {
        "template": "bid_placed.html",
        "subject": "A new bid was placed on your invoice",
        "get_recipients": lambda p: (
            [{"email": p.get("seller_email"), "user_id": p.get("seller_id")}],
            [str(p.get("seller_id"))],
        ),
    },
    "bid.outbid": {
        "template": "bid_placed.html",
        "subject": "You have been outbid",
        "get_recipients": lambda p: (
            [{"email": p.get("previous_bidder_email"), "user_id": p.get("previous_bidder_id")}],
            [str(p.get("previous_bidder_id"))],
        ),
    },
    "auction.extended": {
        "template": "auction_winner.html",
        "subject": "Auction has been extended",
        "get_recipients": lambda p: (
            [{"email": b.get("email"), "user_id": b.get("user_id")} for b in p.get("bidders", [])],
            [str(b.get("user_id")) for b in p.get("bidders", [])],
        ),
    },
    "auction.closed.winner": {
        "template": "auction_winner.html",
        "subject": "Auction closed - you won!",
        "get_recipients": lambda p: (
            [
                {"email": p.get("winner_email"), "user_id": p.get("winner_id")},
                {"email": p.get("seller_email"), "user_id": p.get("seller_id")},
            ],
            [str(p.get("winner_id")), str(p.get("seller_id"))],
        ),
    },
    "auction.closed.loser": {
        "template": "auction_winner.html",
        "subject": "Auction closed - better luck next time",
        "get_recipients": lambda p: (
            [{"email": p.get("loser_email"), "user_id": p.get("loser_id")}],
            [str(p.get("loser_id"))],
        ),
    },
    "auction.expired": {
        "template": "auction_winner.html",
        "subject": "Your auction has expired with no bids",
        "get_recipients": lambda p: (
            [{"email": p.get("seller_email"), "user_id": p.get("seller_id")}],
            [str(p.get("seller_id"))],
        ),
    },
    "wallet.credited": {
        "template": "loan_due.html",
        "subject": "Your wallet has been credited",
        "get_recipients": lambda p: (
            [{"email": p.get("investor_email"), "user_id": p.get("investor_id")}],
            [str(p.get("investor_id"))],
        ),
    },
    "loan.due": {
        "template": "loan_due.html",
        "subject": "Loan repayment is due",
        "get_recipients": lambda p: (
            [{"email": p.get("seller_email"), "user_id": p.get("seller_id")}],
            [str(p.get("seller_id"))],
        ),
    },
    "loan.repaid": {
        "template": "loan_due.html",
        "subject": "Loan has been repaid",
        "get_recipients": lambda p: (
            [
                {"email": p.get("seller_email"), "user_id": p.get("seller_id")},
                {"email": p.get("investor_email"), "user_id": p.get("investor_id")},
            ],
            [str(p.get("seller_id")), str(p.get("investor_id"))],
        ),
    },
    "loan.overdue": {
        "template": "loan_due.html",
        "subject": "Loan is overdue",
        "get_recipients": lambda p: (
            [
                {"email": p.get("seller_email"), "user_id": p.get("seller_id")},
                {"email": p.get("investor_email"), "user_id": p.get("investor_id")},
            ],
            [str(p.get("seller_id")), str(p.get("investor_id"))],
        ),
    },
}


class NotificationHandler:
    """Routes incoming events to the appropriate email and WebSocket channels
    based on the EVENT_MAPPING configuration."""

    def __init__(self):
        self.email_service = EmailService()

    async def handle_event(self, event_type: str, payload: dict) -> None:
        """Process an incoming event by sending emails and WebSocket pushes.

        Args:
            event_type: The dot-notation event type (e.g. 'invoice.listed').
            payload: Event payload containing relevant data and recipient info.
        """
        # TODO: Implement full event handling logic
        # 1. Look up event in EVENT_MAPPING
        # 2. Determine recipients via get_recipients
        # 3. Render email template and send emails
        # 4. Push notification via WebSocket
        # 5. Store notification in notification_store

        mapping = EVENT_MAPPING.get(event_type)
        if not mapping:
            return

        email_targets, ws_targets = mapping["get_recipients"](payload)
        template = mapping["template"]
        subject = mapping["subject"]

        # Render the email HTML
        html_body = EmailService.render_template(template, payload)

        # Send emails to all targets
        for target in email_targets:
            if target.get("email"):
                await self.email_service.send_email(target["email"], subject, html_body)

        # Push via WebSocket
        ws_message = {
            "event_type": event_type,
            "message": subject,
            "payload": payload,
        }
        await ws_manager.broadcast_to_users(ws_targets, ws_message)

        # Store notification for each unique user
        seen_user_ids = set()
        for target in email_targets:
            uid = target.get("user_id")
            if uid and uid not in seen_user_ids:
                seen_user_ids.add(uid)
                notification_store.append(
                    {
                        "id": str(uuid.uuid4()),
                        "user_id": uid,
                        "event_type": event_type,
                        "message": subject,
                        "payload": payload,
                        "created_at": datetime.now(timezone.utc),
                    }
                )


# Singleton instance
notification_handler = NotificationHandler()
