/**
 * WalletService
 * Handles wallet credit, debit, and balance queries.
 */

const Wallet = require('../models/Wallet');
const WalletTransaction = require('../models/WalletTransaction');
const { sequelize } = require('../database');

class WalletService {
  /**
   * Add funds to a user's wallet. Creates the wallet if it does not exist.
   * Idempotency is enforced by the caller (escrow/loan idempotency keys).
   * @param {number} userId
   * @param {string|number} amount
   * @returns {Promise<Wallet>}
   */
  async creditWallet(userId, amount, outerTransaction = null, referenceId = null) {
    const doCredit = async (t) => {
      const [wallet] = await Wallet.findOrCreate({
        where: { user_id: userId },
        defaults: { user_id: userId, balance: 0.00 },
        transaction: t,
      });

      const newBalance = parseFloat(wallet.balance) + parseFloat(amount);
      await wallet.update({ balance: newBalance.toFixed(2) }, { transaction: t });
      await WalletTransaction.create({
        user_id: userId,
        type: 'CREDIT',
        amount: parseFloat(amount).toFixed(2),
        description: 'WALLET_CREDIT',
        reference_id: referenceId || null,
      }, { transaction: t });
      return wallet;
    };

    if (outerTransaction) return await doCredit(outerTransaction);
    return await sequelize.transaction(doCredit);
  }

  /**
   * Deduct funds from a user's wallet.
   * @param {number} userId
   * @param {string|number} amount
   * @returns {Promise<Wallet>}
   * @throws {Error} If wallet not found or insufficient balance.
   */
  async debitWallet(userId, amount, outerTransaction = null) {
    const doDebit = async (t) => {
      const wallet = await Wallet.findOne({
        where: { user_id: userId },
        lock: t.LOCK.UPDATE,
        transaction: t,
      });

      if (!wallet) {
        throw new Error(`You need to top up your wallet before placing a bid.`);
      }

      const current = parseFloat(wallet.balance);
      const debit = parseFloat(amount);

      if (current < debit) {
        throw new Error(`Insufficient balance: have ${current}, need ${debit}`);
      }

      const newBalance = (current - debit).toFixed(2);
      await wallet.update({ balance: newBalance }, { transaction: t });
      await WalletTransaction.create({
        user_id: userId,
        type: 'DEBIT',
        amount: parseFloat(amount).toFixed(2),
        description: 'WALLET_DEBIT',
      }, { transaction: t });
      return wallet;
    };

    if (outerTransaction) return await doDebit(outerTransaction);
    return await sequelize.transaction(doDebit);
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
      throw new Error(`You need to top up your wallet before placing a bid.`);
    }
    return wallet;
  }

  async getTransactions(userId) {
    return await WalletTransaction.findAll({
      where: { user_id: userId },
      order: [['created_at', 'DESC']],
    });
  }
}

module.exports = new WalletService();
