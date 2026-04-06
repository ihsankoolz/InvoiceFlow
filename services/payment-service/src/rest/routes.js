/**
 * REST routes for Payment Service (read-only endpoints).
 *
 * See BUILD_INSTRUCTIONS_V2.md Section 5 — REST Endpoints
 */

const express = require('express');
const router = express.Router();
const WalletService = require('../services/WalletService');
const LoanService = require('../services/LoanService');
const Escrow = require('../models/Escrow');
const WalletTransaction = require('../models/WalletTransaction');

/**
 * GET /wallets/:userId — Get wallet balance.
 */
router.get('/wallets/:userId', async (req, res) => {
  try {
    const userId = parseInt(req.params.userId, 10);
    const wallet = await WalletService.getBalance(userId);
    const lockedEscrows = await Escrow.findAll({ where: { investor_id: userId, status: 'LOCKED' } });
    const lockedBalance = lockedEscrows.reduce((sum, e) => sum + parseFloat(e.amount), 0);
    res.json({
      user_id: wallet.user_id,
      balance: String(wallet.balance),
      locked_balance: lockedBalance.toFixed(2),
      currency: wallet.currency,
    });
  } catch (err) {
    res.status(404).json({ error: err.message });
  }
});

function serializeLoan(loan) {
  const data = loan.toJSON();
  return {
    ...data,
    due_date: data.due_date ? new Date(data.due_date).toISOString() : null,
    grace_end: data.grace_end ? new Date(data.grace_end).toISOString() : null,
  };
}

/**
 * GET /loans/:loanId — Get loan details.
 */
router.get('/loans/:loanId', async (req, res) => {
  try {
    const loan = await LoanService.getLoan(req.params.loanId);
    res.json(serializeLoan(loan));
  } catch (err) {
    res.status(404).json({ error: err.message });
  }
});

/**
 * GET /loans?investor_id=:id — Get loans by investor.
 * GET /loans?seller_id=:id  — Get loans by seller.
 */
router.get('/loans', async (req, res) => {
  try {
    if (req.query.seller_id) {
      const loans = await LoanService.getLoansBySeller(parseInt(req.query.seller_id, 10));
      return res.json(loans.map(serializeLoan));
    }
    const loans = await LoanService.getLoansByInvestor(parseInt(req.query.investor_id, 10));
    res.json(loans.map(serializeLoan));
  } catch (err) {
    res.status(400).json({ error: err.message });
  }
});

/**
 * GET /escrows?investor_id=:id — Get active (LOCKED) escrows for an investor.
 */
router.get('/escrows', async (req, res) => {
  try {
    const escrows = await Escrow.findAll({
      where: { investor_id: parseInt(req.query.investor_id, 10), status: 'LOCKED' },
    });
    res.json(escrows);
  } catch (err) {
    res.status(400).json({ error: err.message });
  }
});

/**
 * GET /transactions?user_id=:id — Get wallet transaction history for a user.
 */
router.get('/transactions', async (req, res) => {
  try {
    const transactions = await WalletService.getTransactions(parseInt(req.query.user_id, 10));
    res.json(transactions);
  } catch (err) {
    res.status(400).json({ error: err.message });
  }
});

module.exports = router;
