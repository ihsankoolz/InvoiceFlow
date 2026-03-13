/**
 * WalletService
 * Handles wallet credit, debit, and balance queries.
 */

const Wallet = require('../models/Wallet');
const { sequelize } = require('../database');

class WalletService {
  /**
   * Add funds to a user's wallet. Creates the wallet if it does not exist.
   * @param {number} userId - The ID of the wallet owner.
   * @param {string|number} amount - The amount to credit.
   * @param {string} idempotencyKey - Unique key to prevent duplicate credits.
   * @returns {Promise<Wallet>} The updated wallet record.
   */
  async creditWallet(userId, amount, idempotencyKey) {
    // TODO: Implement idempotency check
    // TODO: Find or create wallet for userId
    // TODO: Increment balance by amount within a transaction
    // TODO: Return updated wallet
    throw new Error('Not implemented');
  }

  /**
   * Deduct funds from a user's wallet.
   * @param {number} userId - The ID of the wallet owner.
   * @param {string|number} amount - The amount to debit.
   * @returns {Promise<Wallet>} The updated wallet record.
   * @throws {Error} If insufficient balance.
   */
  async debitWallet(userId, amount) {
    // TODO: Find wallet for userId (throw if not found)
    // TODO: Verify sufficient balance
    // TODO: Decrement balance by amount within a transaction
    // TODO: Return updated wallet
    throw new Error('Not implemented');
  }

  /**
   * Retrieve the current wallet for a user.
   * @param {number} userId - The ID of the wallet owner.
   * @returns {Promise<Wallet>} The wallet record.
   * @throws {Error} If wallet not found.
   */
  async getBalance(userId) {
    // TODO: Find wallet by user_id
    // TODO: Throw if not found
    // TODO: Return wallet
    throw new Error('Not implemented');
  }
}

module.exports = new WalletService();
