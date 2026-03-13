/**
 * LoanService
 * Manages loan lifecycle — creation, status updates, fund release, and penalties.
 */

const { v4: uuidv4 } = require('uuid');
const Loan = require('../models/Loan');
const walletService = require('./WalletService');
const { sequelize } = require('../database');

class LoanService {
  /**
   * Create a new loan record.
   * @param {Object} data - Loan creation payload.
   * @param {string} data.invoice_token - The invoice this loan is for.
   * @param {number} data.investor_id - The investor funding the loan.
   * @param {number} data.seller_id - The seller receiving funds.
   * @param {string|number} data.principal - The loan principal amount.
   * @param {string} data.due_date - The repayment due date (YYYY-MM-DD).
   * @param {string} idempotencyKey - Unique key to prevent duplicate loans.
   * @returns {Promise<Loan>} The created loan record.
   */
  async createLoan(data, idempotencyKey) {
    // TODO: Check idempotency — return existing loan if duplicate
    // TODO: Generate loan_id via uuid
    // TODO: Create loan record with status ACTIVE
    // TODO: Return created loan
    throw new Error('Not implemented');
  }

  /**
   * Retrieve a loan by its loan_id.
   * @param {string} loanId - The unique loan identifier.
   * @returns {Promise<Loan>} The loan record.
   * @throws {Error} If loan not found.
   */
  async getLoan(loanId) {
    // TODO: Find loan by loan_id
    // TODO: Throw if not found
    // TODO: Return loan
    throw new Error('Not implemented');
  }

  /**
   * Update the status of a loan.
   * @param {string} loanId - The unique loan identifier.
   * @param {string} status - The new status (ACTIVE | DUE | REPAID | OVERDUE).
   * @returns {Promise<Loan>} The updated loan record.
   * @throws {Error} If loan not found or invalid status transition.
   */
  async updateStatus(loanId, status) {
    // TODO: Find loan by loan_id
    // TODO: Validate status transition
    // TODO: Update status
    // TODO: Return updated loan
    throw new Error('Not implemented');
  }

  /**
   * Release funds to the seller's wallet after escrow conversion.
   * @param {number} sellerId - The seller to credit.
   * @param {string|number} amount - The amount to release.
   * @param {string} idempotencyKey - Unique key to prevent duplicate releases.
   * @returns {Promise<{success: boolean, message: string}>} Transfer result.
   */
  async releaseFundsToSeller(sellerId, amount, idempotencyKey) {
    // TODO: Credit seller wallet via walletService.creditWallet
    // TODO: Return success response
    throw new Error('Not implemented');
  }

  /**
   * Calculate penalty for an overdue loan (5% of principal).
   * @param {string} loanId - The unique loan identifier.
   * @returns {Promise<string>} The penalty amount as a decimal string.
   * @throws {Error} If loan not found.
   */
  async calculatePenalty(loanId) {
    // TODO: Find loan by loan_id
    // TODO: Calculate 5% of principal
    // TODO: Update penalty_amount on loan record
    // TODO: Return penalty amount
    throw new Error('Not implemented');
  }
}

module.exports = new LoanService();
