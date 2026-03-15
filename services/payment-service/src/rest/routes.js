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

/**
 * GET /wallets/:userId — Get wallet balance.
 */
router.get('/wallets/:userId', async (req, res) => {
  try {
    const wallet = await WalletService.getBalance(parseInt(req.params.userId, 10));
    res.json({ user_id: wallet.user_id, balance: String(wallet.balance), currency: wallet.currency });
  } catch (err) {
    res.status(404).json({ error: err.message });
  }
});

/**
 * GET /loans/:loanId — Get loan details.
 */
router.get('/loans/:loanId', async (req, res) => {
  try {
    const loan = await LoanService.getLoan(req.params.loanId);
    res.json(loan);
  } catch (err) {
    res.status(404).json({ error: err.message });
  }
});

/**
 * GET /loans?investor_id=:id — Get loans by investor.
 */
router.get('/loans', async (req, res) => {
  try {
    const loans = await LoanService.getLoansByInvestor(parseInt(req.query.investor_id, 10));
    res.json(loans);
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

module.exports = router;
