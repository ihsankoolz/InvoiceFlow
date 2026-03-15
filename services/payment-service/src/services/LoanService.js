/**
 * LoanService
 * Manages loan lifecycle — creation, status updates, fund release, and penalties.
 */

const { v4: uuidv4 } = require('uuid');
const Loan = require('../models/Loan');
const walletService = require('./WalletService');
const { sequelize } = require('../database');

const VALID_TRANSITIONS = {
  ACTIVE: ['DUE'],
  DUE: ['REPAID', 'OVERDUE'],
  REPAID: [],
  OVERDUE: [],
};

class LoanService {
  /**
   * Create a new loan record.
   * @param {Object} data - { invoice_token, investor_id, seller_id, principal, due_date }
   * @param {string} idempotencyKey
   * @returns {Promise<Loan>}
   */
  async createLoan(data, idempotencyKey) {
    // Idempotency: return existing loan if key already used
    const existing = await Loan.findOne({ where: { loan_id: idempotencyKey } });
    if (existing) return existing;

    const loan = await Loan.create({
      loan_id: uuidv4(),
      invoice_token: data.invoice_token,
      investor_id: data.investor_id,
      seller_id: data.seller_id,
      principal: parseFloat(data.principal).toFixed(2),
      due_date: data.due_date,
      status: 'ACTIVE',
    });

    return loan;
  }

  /**
   * Retrieve a loan by its loan_id.
   * @param {string} loanId
   * @returns {Promise<Loan>}
   */
  async getLoan(loanId) {
    const loan = await Loan.findOne({ where: { loan_id: loanId } });
    if (!loan) throw new Error(`Loan not found: ${loanId}`);
    return loan;
  }

  /**
   * Update the status of a loan with transition validation.
   * @param {string} loanId
   * @param {string} status - DUE | REPAID | OVERDUE
   * @returns {Promise<Loan>}
   */
  async updateStatus(loanId, status) {
    const loan = await this.getLoan(loanId);
    const allowed = VALID_TRANSITIONS[loan.status] || [];

    if (!allowed.includes(status)) {
      throw new Error(`Invalid status transition: ${loan.status} → ${status}`);
    }

    await loan.update({ status });
    return loan;
  }

  /**
   * Credit seller wallet with loan principal (called after escrow conversion).
   * @param {number} sellerId
   * @param {string|number} amount
   * @param {string} idempotencyKey
   * @returns {Promise<{success: boolean, message: string}>}
   */
  async releaseFundsToSeller(sellerId, amount, idempotencyKey) {
    await walletService.creditWallet(sellerId, amount);
    return { success: true, message: `Credited ${amount} to seller ${sellerId}` };
  }

  /**
   * Calculate and record a 5% penalty for an overdue loan.
   * @param {string} loanId
   * @returns {Promise<string>} The penalty amount as a decimal string.
   */
  async calculatePenalty(loanId) {
    const loan = await this.getLoan(loanId);
    const penalty = (parseFloat(loan.principal) * 0.05).toFixed(2);
    await loan.update({ penalty_amount: penalty });
    return penalty;
  }

  /**
   * Get all loans for a given investor.
   * @param {number} investorId
   * @returns {Promise<Loan[]>}
   */
  async getLoansByInvestor(investorId) {
    return await Loan.findAll({ where: { investor_id: investorId } });
  }
}

module.exports = new LoanService();
