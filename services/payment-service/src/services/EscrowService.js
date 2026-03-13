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
   * @param {number} investorId - The investor placing the bid.
   * @param {string} invoiceToken - The invoice being bid on.
   * @param {string|number} amount - The bid amount to lock.
   * @param {string} idempotencyKey - Unique key to prevent duplicate locks.
   * @returns {Promise<Escrow>} The created escrow record.
   * @throws {Error} If insufficient wallet balance or duplicate escrow.
   */
  async lockEscrow(investorId, invoiceToken, amount, idempotencyKey) {
    // TODO: Check idempotency — return existing escrow if key already used
    // TODO: Debit investor wallet by amount (walletService.debitWallet)
    // TODO: Create escrow record with status LOCKED
    // TODO: Return escrow
    throw new Error('Not implemented');
  }

  /**
   * Release escrowed funds back to the investor's wallet.
   * Marks the escrow as RELEASED and credits the wallet.
   * @param {number} investorId - The investor whose escrow to release.
   * @param {string} invoiceToken - The invoice token identifying the escrow.
   * @param {string} idempotencyKey - Unique key to prevent duplicate releases.
   * @returns {Promise<Escrow>} The updated escrow record.
   * @throws {Error} If escrow not found or already released/converted.
   */
  async releaseEscrow(investorId, invoiceToken, idempotencyKey) {
    // TODO: Find LOCKED escrow for (investorId, invoiceToken)
    // TODO: Credit investor wallet with escrow amount (walletService.creditWallet)
    // TODO: Update escrow status to RELEASED
    // TODO: Return updated escrow
    throw new Error('Not implemented');
  }

  /**
   * Convert a locked escrow to a loan (mark as CONVERTED).
   * Does not move funds — the loan service handles disbursement.
   * @param {number} investorId - The investor whose escrow to convert.
   * @param {string} invoiceToken - The invoice token identifying the escrow.
   * @param {string} idempotencyKey - Unique key to prevent duplicate conversions.
   * @returns {Promise<Escrow>} The updated escrow record.
   * @throws {Error} If escrow not found or not in LOCKED status.
   */
  async convertToLoan(investorId, invoiceToken, idempotencyKey) {
    // TODO: Find LOCKED escrow for (investorId, invoiceToken)
    // TODO: Update escrow status to CONVERTED
    // TODO: Return updated escrow
    throw new Error('Not implemented');
  }
}

module.exports = new EscrowService();
