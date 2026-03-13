/**
 * RabbitMQ consumer for Payment Service.
 *
 * Subscribes to:
 * - bid.outbid (queue: payment_outbid_updates) → release previous bidder's escrow
 * - loan.repaid (queue: payment_repaid_updates) → credit investor wallet
 * - loan.overdue (queue: payment_loan_updates) → calculate 5% penalty
 *
 * See BUILD_INSTRUCTIONS_V2.md Section 5 — RabbitMQ Consumer
 */

const amqplib = require('amqplib');
const config = require('../config');

const EXCHANGE = 'invoiceflow_events';

const SUBSCRIPTIONS = [
  {
    queue: 'payment_outbid_updates',
    routingKey: 'bid.outbid',
    handler: handleOutbid,
  },
  {
    queue: 'payment_repaid_updates',
    routingKey: 'loan.repaid',
    handler: handleRepaid,
  },
  {
    queue: 'payment_loan_updates',
    routingKey: 'loan.overdue',
    handler: handleOverdue,
  },
];

/**
 * Handle bid.outbid — release previous bidder's escrow back to wallet.
 * @param {object} payload - { invoice_token, outbid_investor_id, outbid_amount, ... }
 */
async function handleOutbid(payload) {
  // TODO: Implement
  // 1. Call EscrowService.releaseEscrow(payload.outbid_investor_id, payload.invoice_token)
  console.log('[payment-consumer] bid.outbid received:', payload);
}

/**
 * Handle loan.repaid — credit investor wallet with repaid principal.
 * @param {object} payload - { loan_id, investor_id, principal, ... }
 */
async function handleRepaid(payload) {
  // TODO: Implement
  // 1. Call WalletService.creditWallet(payload.investor_id, payload.principal)
  console.log('[payment-consumer] loan.repaid received:', payload);
}

/**
 * Handle loan.overdue — calculate and apply 5% penalty.
 * @param {object} payload - { loan_id, ... }
 */
async function handleOverdue(payload) {
  // TODO: Implement
  // 1. Call LoanService.calculatePenalty(payload.loan_id)
  console.log('[payment-consumer] loan.overdue received:', payload);
}

/**
 * Start the RabbitMQ consumer, binding all queues.
 */
async function startConsumer() {
  const connection = await amqplib.connect(config.rabbitmqUrl);
  const channel = await connection.createChannel();

  await channel.assertExchange(EXCHANGE, 'topic', { durable: true });

  for (const sub of SUBSCRIPTIONS) {
    await channel.assertQueue(sub.queue, { durable: true });
    await channel.bindQueue(sub.queue, EXCHANGE, sub.routingKey);

    channel.consume(sub.queue, async (msg) => {
      if (!msg) return;
      try {
        const payload = JSON.parse(msg.content.toString());
        await sub.handler(payload);
        channel.ack(msg);
      } catch (err) {
        console.error(`[payment-consumer] Error processing ${sub.routingKey}:`, err.message);
        channel.nack(msg, false, false);
      }
    });

    console.log(`[payment-consumer] Listening on queue: ${sub.queue} (${sub.routingKey})`);
  }
}

module.exports = { startConsumer };
