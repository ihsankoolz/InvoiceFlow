/**
 * EscrowService
 * Manages locking, releasing, and converting escrow funds.
 */

const Escrow = require('../models/Escrow');
const walletService = require('./WalletService');
const { sequelize } = require('../database');

class EscrowService {
  /**
   * Lock funds in escrow for an invoice bid.
   * Debits the investor's wallet and creates an escrow record.
   * @param {number} investorId
   * @param {string} invoiceToken
   * @param {string|number} amount
   * @param {string} idempotencyKey
   * @returns {Promise<Escrow>}
   */
  async lockEscrow(investorId, invoiceToken, amount, idempotencyKey) {
    // Idempotency: return existing escrow if key already used
    const existing = await Escrow.findOne({ where: { idempotency_key: idempotencyKey } });
    if (existing) return existing;

    return await sequelize.transaction(async (t) => {
      // Debit wallet within the same transaction — rolls back if escrow update/create fails
      await walletService.debitWallet(investorId, amount, t);

      // Reuse existing escrow record (RELEASED) to avoid unique_escrow constraint violation
      const existing = await Escrow.findOne({
        where: { investor_id: investorId, invoice_token: invoiceToken },
        lock: t.LOCK.UPDATE,
        transaction: t,
      });

      if (existing) {
        await existing.update({
          amount: parseFloat(amount).toFixed(2),
          status: 'LOCKED',
          idempotency_key: idempotencyKey,
        }, { transaction: t });
        return existing;
      }

      const escrow = await Escrow.create({
        investor_id: investorId,
        invoice_token: invoiceToken,
        amount: parseFloat(amount).toFixed(2),
        status: 'LOCKED',
        idempotency_key: idempotencyKey,
      }, { transaction: t });

      return escrow;
    });
  }

  /**
   * Release escrowed funds back to the investor's wallet.
   * @param {number} investorId
   * @param {string} invoiceToken
   * @param {string} idempotencyKey
   * @returns {Promise<Escrow>}
   */
  async releaseEscrow(investorId, invoiceToken, idempotencyKey) {
    return await sequelize.transaction(async (t) => {
      const escrow = await Escrow.findOne({
        where: { investor_id: investorId, invoice_token: invoiceToken, status: 'LOCKED' },
        lock: t.LOCK.UPDATE,
        transaction: t,
      });

      if (!escrow) {
        throw new Error(`No LOCKED escrow found for investor ${investorId} on token ${invoiceToken}`);
      }

      await walletService.creditWallet(investorId, escrow.amount, t);
      await escrow.update({ status: 'RELEASED' }, { transaction: t });
      return escrow;
    });
  }

  /**
   * Convert a locked escrow to a loan (mark as CONVERTED).
   * Funds stay in the system — LoanService handles disbursement.
   * @param {number} investorId
   * @param {string} invoiceToken
   * @param {string} idempotencyKey
   * @returns {Promise<Escrow>}
   */
  async convertToLoan(investorId, invoiceToken, idempotencyKey) {
    // Idempotency: already converted
    const existing = await Escrow.findOne({
      where: { investor_id: investorId, invoice_token: invoiceToken, status: 'CONVERTED' },
    });
    if (existing) return existing;

    const escrow = await Escrow.findOne({
      where: { investor_id: investorId, invoice_token: invoiceToken, status: 'LOCKED' },
    });

    if (!escrow) {
      throw new Error(`No LOCKED escrow found for investor ${investorId} on token ${invoiceToken}`);
    }

    await escrow.update({ status: 'CONVERTED' });
    return escrow;
  }
}

module.exports = new EscrowService();
