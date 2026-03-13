/**
 * REST routes for Payment Service (read-only endpoints).
 *
 * See BUILD_INSTRUCTIONS_V2.md Section 5 — REST Endpoints
 */

const express = require('express');
const router = express.Router();

/**
 * GET /wallets/:userId — Get wallet balance.
 */
router.get('/wallets/:userId', async (req, res) => {
  // TODO: Implement
  // 1. Call WalletService.getBalance(req.params.userId)
  // 2. Return { user_id, balance, currency }
  res.status(501).json({ error: 'Not implemented yet' });
});

/**
 * GET /loans/:loanId — Get loan details.
 */
router.get('/loans/:loanId', async (req, res) => {
  // TODO: Implement
  // 1. Call LoanService.getLoan(req.params.loanId)
  // 2. Return loan details
  res.status(501).json({ error: 'Not implemented yet' });
});

/**
 * GET /loans?investor_id=:id — Get loans by investor.
 */
router.get('/loans', async (req, res) => {
  // TODO: Implement
  // 1. Call LoanService.getLoansByInvestor(req.query.investor_id)
  // 2. Return list of loans
  res.status(501).json({ error: 'Not implemented yet' });
});

/**
 * GET /escrows?investor_id=:id — Get active escrows for an investor.
 */
router.get('/escrows', async (req, res) => {
  // TODO: Implement
  // 1. Query escrows where investor_id = req.query.investor_id and status = 'LOCKED'
  // 2. Return list of escrows
  res.status(501).json({ error: 'Not implemented yet' });
});

module.exports = router;
