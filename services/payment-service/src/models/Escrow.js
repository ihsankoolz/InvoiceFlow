/**
 * Escrow Sequelize Model
 * Represents locked funds for an invoice bid.
 */

const { DataTypes } = require('sequelize');
const { sequelize } = require('../database');

const Escrow = sequelize.define('Escrow', {
  id: {
    type: DataTypes.INTEGER,
    autoIncrement: true,
    primaryKey: true,
  },
  investor_id: {
    type: DataTypes.INTEGER,
    allowNull: false,
  },
  invoice_token: {
    type: DataTypes.STRING(36),
    allowNull: false,
  },
  amount: {
    type: DataTypes.DECIMAL(12, 2),
    allowNull: false,
  },
  status: {
    type: DataTypes.ENUM('LOCKED', 'CONVERTED', 'RELEASED'),
    defaultValue: 'LOCKED',
  },
  idempotency_key: {
    type: DataTypes.STRING(100),
    unique: true,
  },
}, {
  tableName: 'escrows',
  timestamps: true,
  createdAt: 'created_at',
  updatedAt: false,
  indexes: [
    {
      unique: true,
      fields: ['investor_id', 'invoice_token'],
      name: 'unique_escrow',
    },
  ],
});

module.exports = Escrow;
