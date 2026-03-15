/**
 * WalletService
 * Handles wallet credit, debit, and balance queries.
 */

const Wallet = require('../models/Wallet');
const { sequelize } = require('../database');

class WalletService {
  /**
   * Add funds to a user's wallet. Creates the wallet if it does not exist.
   * Idempotency is enforced by the caller (escrow/loan idempotency keys).
   * @param {number} userId
   * @param {string|number} amount
   * @returns {Promise<Wallet>}
   */
  async creditWallet(userId, amount) {
    return await sequelize.transaction(async (t) => {
      const [wallet] = await Wallet.findOrCreate({
        where: { user_id: userId },
        defaults: { user_id: userId, balance: 0.00 },
        transaction: t,
      });

      const newBalance = parseFloat(wallet.balance) + parseFloat(amount);
      await wallet.update({ balance: newBalance.toFixed(2) }, { transaction: t });
      return wallet;
    });
  }

  /**
   * Deduct funds from a user's wallet.
   * @param {number} userId
   * @param {string|number} amount
   * @returns {Promise<Wallet>}
   * @throws {Error} If wallet not found or insufficient balance.
   */
  async debitWallet(userId, amount) {
    return await sequelize.transaction(async (t) => {
      const wallet = await Wallet.findOne({
        where: { user_id: userId },
        lock: t.LOCK.UPDATE,
        transaction: t,
      });

      if (!wallet) {
        throw new Error(`Wallet not found for user ${userId}`);
      }

      const current = parseFloat(wallet.balance);
      const debit = parseFloat(amount);

      if (current < debit) {
        throw new Error(`Insufficient balance: have ${current}, need ${debit}`);
      }

      const newBalance = (current - debit).toFixed(2);
      await wallet.update({ balance: newBalance }, { transaction: t });
      return wallet;
    });
  }

  /**
   * Retrieve the current wallet for a user.
   * @param {number} userId
   * @returns {Promise<Wallet>}
   * @throws {Error} If wallet not found.
   */
  async getBalance(userId) {
    const wallet = await Wallet.findOne({ where: { user_id: userId } });
    if (!wallet) {
      throw new Error(`Wallet not found for user ${userId}`);
    }
    return wallet;
  }
}

module.exports = new WalletService();
