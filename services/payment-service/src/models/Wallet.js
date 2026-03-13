/**
 * Wallet Sequelize Model
 * Represents a user's wallet with a monetary balance.
 */

const { DataTypes } = require('sequelize');
const { sequelize } = require('../database');

const Wallet = sequelize.define('Wallet', {
  id: {
    type: DataTypes.INTEGER,
    autoIncrement: true,
    primaryKey: true,
  },
  user_id: {
    type: DataTypes.INTEGER,
    unique: true,
    allowNull: false,
  },
  balance: {
    type: DataTypes.DECIMAL(12, 2),
    defaultValue: 0.00,
  },
  currency: {
    type: DataTypes.STRING(3),
    defaultValue: 'SGD',
  },
}, {
  tableName: 'wallets',
  timestamps: true,
  createdAt: 'created_at',
  updatedAt: 'updated_at',
});

module.exports = Wallet;
