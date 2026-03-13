/**
 * gRPC method handlers for PaymentService.
 * Each handler receives (call, callback) and delegates to the appropriate service class.
 *
 * See BUILD_INSTRUCTIONS_V2.md Section 5 — gRPC Service Definition
 */

const WalletService = require('../services/WalletService');
const EscrowService = require('../services/EscrowService');
const LoanService = require('../services/LoanService');

/**
 * LockEscrow — debit investor wallet, create escrow record.
 * @param {object} call - { investor_id, invoice_token, amount, idempotency_key }
 * @param {function} callback
 */
async function lockEscrow(call, callback) {
  // TODO: Implement
  // 1. Parse call.request (investor_id, invoice_token, amount, idempotency_key)
  // 2. Check idempotency — if key already exists, return existing escrow
  // 3. Call WalletService.debitWallet(investor_id, amount)
  // 4. Call EscrowService.lockEscrow(investor_id, invoice_token, amount, idempotency_key)
  // 5. Return EscrowResponse { id, status, amount }
  callback({ code: 12, message: 'LockEscrow not implemented yet' });
}

/**
 * ReleaseEscrow — return escrowed funds to investor wallet, mark RELEASED.
 * @param {object} call - { investor_id, invoice_token, idempotency_key }
 * @param {function} callback
 */
async function releaseEscrow(call, callback) {
  // TODO: Implement
  // 1. Find escrow by investor_id + invoice_token
  // 2. Credit wallet with escrow amount
  // 3. Mark escrow RELEASED
  // 4. Return EscrowResponse
  callback({ code: 12, message: 'ReleaseEscrow not implemented yet' });
}

/**
 * ConvertEscrowToLoan — mark escrow CONVERTED (funds stay in system for loan).
 * @param {object} call - { investor_id, invoice_token, idempotency_key }
 * @param {function} callback
 */
async function convertEscrowToLoan(call, callback) {
  // TODO: Implement
  // 1. Find escrow by investor_id + invoice_token
  // 2. Mark escrow CONVERTED
  // 3. Return EscrowResponse
  callback({ code: 12, message: 'ConvertEscrowToLoan not implemented yet' });
}

/**
 * CreateLoan — create a new loan record.
 * @param {object} call - { invoice_token, investor_id, seller_id, principal, due_date, idempotency_key }
 * @param {function} callback
 */
async function createLoan(call, callback) {
  // TODO: Implement
  // 1. Call LoanService.createLoan(data, idempotencyKey)
  // 2. Return LoanResponse { loan_id, status, principal, due_date, investor_id, seller_id }
  callback({ code: 12, message: 'CreateLoan not implemented yet' });
}

/**
 * ReleaseFundsToSeller — credit seller wallet with loan principal.
 * @param {object} call - { seller_id, amount, invoice_token, idempotency_key }
 * @param {function} callback
 */
async function releaseFundsToSeller(call, callback) {
  // TODO: Implement
  // 1. Call LoanService.releaseFundsToSeller(sellerId, amount, idempotencyKey)
  // 2. Return TransferResponse { success, message }
  callback({ code: 12, message: 'ReleaseFundsToSeller not implemented yet' });
}

/**
 * CreditWallet — add funds to a user wallet (used for Stripe top-up and escrow release).
 * @param {object} call - { user_id, amount, idempotency_key }
 * @param {function} callback
 */
async function creditWallet(call, callback) {
  // TODO: Implement
  // 1. Call WalletService.creditWallet(userId, amount, idempotencyKey)
  // 2. Return WalletResponse { user_id, balance }
  callback({ code: 12, message: 'CreditWallet not implemented yet' });
}

/**
 * GetLoan — fetch loan by loan_id.
 * @param {object} call - { loan_id }
 * @param {function} callback
 */
async function getLoan(call, callback) {
  // TODO: Implement
  // 1. Call LoanService.getLoan(loanId)
  // 2. Return LoanResponse
  callback({ code: 12, message: 'GetLoan not implemented yet' });
}

/**
 * UpdateLoanStatus — update loan status (DUE, REPAID, OVERDUE).
 * @param {object} call - { loan_id, status }
 * @param {function} callback
 */
async function updateLoanStatus(call, callback) {
  // TODO: Implement
  // 1. Call LoanService.updateStatus(loanId, status)
  // 2. Return LoanResponse
  callback({ code: 12, message: 'UpdateLoanStatus not implemented yet' });
}

module.exports = {
  lockEscrow,
  releaseEscrow,
  convertEscrowToLoan,
  createLoan,
  releaseFundsToSeller,
  creditWallet,
  getLoan,
  updateLoanStatus,
};
