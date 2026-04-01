"""Event type constants for the InvoiceFlow platform."""

# Invoice events
INVOICE_LISTED = "invoice.listed"
INVOICE_FUNDED = "invoice.funded"
INVOICE_CLOSED = "invoice.closed"

# Bid events
BID_PLACED = "bid.placed"
BID_ACCEPTED = "bid.accepted"
BID_REJECTED = "bid.rejected"

# Auction events
AUCTION_CLOSED_FUNDED = "auction.closed.funded"
AUCTION_CLOSED_EXPIRED = "auction.closed.expired"
AUCTION_EXTENDED = "auction.extended"

# Loan events
LOAN_CREATED = "loan.created"
LOAN_REPAID = "loan.repaid"
LOAN_OVERDUE = "loan.overdue"

# Wallet events
WALLET_TOPPED_UP = "wallet.topped_up"

# Stripe events
STRIPE_CHECKOUT_COMPLETED = "stripe.checkout.completed"
