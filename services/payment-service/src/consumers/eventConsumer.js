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
const EscrowService = require('../services/EscrowService');
const WalletService = require('../services/WalletService');
const LoanService = require('../services/LoanService');

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
 */
async function handleOutbid(payload) {
  const { invoice_token, outbid_investor_id } = payload;
  await EscrowService.releaseEscrow(
    outbid_investor_id,
    invoice_token,
    `release-outbid-${invoice_token}-${outbid_investor_id}`,
  );
  console.log(`[payment-consumer] bid.outbid: released escrow for investor ${outbid_investor_id} on ${invoice_token}`);
}

/**
 * Handle loan.repaid — credit investor wallet with repaid principal.
 */
async function handleRepaid(payload) {
  const { investor_id, principal } = payload;
  await WalletService.creditWallet(investor_id, principal);
  console.log(`[payment-consumer] loan.repaid: credited ${principal} to investor ${investor_id}`);
}

/**
 * Handle loan.overdue — calculate and apply 5% penalty.
 */
async function handleOverdue(payload) {
  const { loan_id } = payload;
  const penalty = await LoanService.calculatePenalty(loan_id);
  console.log(`[payment-consumer] loan.overdue: applied penalty ${penalty} on loan ${loan_id}`);
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
