/**
 * WalletTransaction Sequelize Model
 * Records every credit and debit against a user's wallet.
 */

const { DataTypes } = require('sequelize');
const { sequelize } = require('../database');

const WalletTransaction = sequelize.define('WalletTransaction', {
  id: {
    type: DataTypes.INTEGER,
    autoIncrement: true,
    primaryKey: true,
  },
  user_id: {
    type: DataTypes.INTEGER,
    allowNull: false,
  },
  type: {
    type: DataTypes.ENUM('CREDIT', 'DEBIT'),
    allowNull: false,
  },
  amount: {
    type: DataTypes.DECIMAL(12, 2),
    allowNull: false,
  },
  description: {
    type: DataTypes.STRING(100),
    allowNull: false,
  },
  reference_id: {
    type: DataTypes.STRING(100),
    allowNull: true,
  },
}, {
  tableName: 'wallet_transactions',
  timestamps: true,
  createdAt: 'created_at',
  updatedAt: false,
});

module.exports = WalletTransaction;
