/**
 * Loan Sequelize Model
 * Represents an active loan created from a converted escrow.
 */

const { DataTypes } = require('sequelize');
const { sequelize } = require('../database');

const Loan = sequelize.define('Loan', {
  id: {
    type: DataTypes.INTEGER,
    autoIncrement: true,
    primaryKey: true,
  },
  loan_id: {
    type: DataTypes.STRING(36),
    unique: true,
    allowNull: false,
  },
  invoice_token: {
    type: DataTypes.STRING(36),
    allowNull: false,
  },
  investor_id: {
    type: DataTypes.INTEGER,
    allowNull: false,
  },
  seller_id: {
    type: DataTypes.INTEGER,
    allowNull: false,
  },
  principal: {
    type: DataTypes.DECIMAL(12, 2),
    allowNull: false,
  },
  bid_amount: {
    type: DataTypes.DECIMAL(12, 2),
    allowNull: false,
  },
  penalty_amount: {
    type: DataTypes.DECIMAL(12, 2),
    defaultValue: 0.00,
  },
  status: {
    type: DataTypes.ENUM('ACTIVE', 'DUE', 'REPAID', 'OVERDUE'),
    defaultValue: 'ACTIVE',
  },
  due_date: {
    type: DataTypes.DATE,
    allowNull: false,
  },
}, {
  tableName: 'loans',
  timestamps: true,
  createdAt: 'created_at',
  updatedAt: 'updated_at',
});

module.exports = Loan;
