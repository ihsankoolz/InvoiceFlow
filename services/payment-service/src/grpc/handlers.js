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
 */
async function lockEscrow(call, callback) {
  try {
    const { investor_id, invoice_token, amount, idempotency_key } = call.request;
    const escrow = await EscrowService.lockEscrow(investor_id, invoice_token, amount, idempotency_key);
    callback(null, { id: String(escrow.id), status: escrow.status, amount: String(escrow.amount) });
  } catch (err) {
    callback({ code: 3, message: err.message }); // INVALID_ARGUMENT
  }
}

/**
 * ReleaseEscrow — return escrowed funds to investor wallet, mark RELEASED.
 */
async function releaseEscrow(call, callback) {
  try {
    const { investor_id, invoice_token, idempotency_key } = call.request;
    const escrow = await EscrowService.releaseEscrow(investor_id, invoice_token, idempotency_key);
    callback(null, { id: String(escrow.id), status: escrow.status, amount: String(escrow.amount) });
  } catch (err) {
    callback({ code: 5, message: err.message }); // NOT_FOUND
  }
}

/**
 * ConvertEscrowToLoan — mark escrow CONVERTED (funds stay in system for loan).
 */
async function convertEscrowToLoan(call, callback) {
  try {
    const { investor_id, invoice_token, idempotency_key } = call.request;
    const escrow = await EscrowService.convertToLoan(investor_id, invoice_token, idempotency_key);
    callback(null, { id: String(escrow.id), status: escrow.status, amount: String(escrow.amount) });
  } catch (err) {
    callback({ code: 5, message: err.message });
  }
}

/**
 * CreateLoan — create a new loan record.
 */
async function createLoan(call, callback) {
  try {
    const { invoice_token, investor_id, seller_id, principal, due_date, idempotency_key } = call.request;
    const loan = await LoanService.createLoan(
      { invoice_token, investor_id, seller_id, principal, due_date },
      idempotency_key,
    );
    callback(null, {
      loan_id: loan.loan_id,
      status: loan.status,
      principal: String(loan.principal),
      due_date: String(loan.due_date),
      investor_id: loan.investor_id,
      seller_id: loan.seller_id,
    });
  } catch (err) {
    callback({ code: 3, message: err.message });
  }
}

/**
 * ReleaseFundsToSeller — credit seller wallet with loan principal.
 */
async function releaseFundsToSeller(call, callback) {
  try {
    const { seller_id, amount, idempotency_key } = call.request;
    const result = await LoanService.releaseFundsToSeller(seller_id, amount, idempotency_key);
    callback(null, { success: result.success, message: result.message });
  } catch (err) {
    callback({ code: 3, message: err.message });
  }
}

/**
 * CreditWallet — add funds to a user wallet (Stripe top-up or escrow release).
 */
async function creditWallet(call, callback) {
  try {
    const { user_id, amount } = call.request;
    const wallet = await WalletService.creditWallet(user_id, amount);
    callback(null, { user_id: wallet.user_id, balance: String(wallet.balance) });
  } catch (err) {
    callback({ code: 3, message: err.message });
  }
}

/**
 * GetLoan — fetch loan by loan_id.
 */
async function getLoan(call, callback) {
  try {
    const { loan_id } = call.request;
    const loan = await LoanService.getLoan(loan_id);
    callback(null, {
      loan_id: loan.loan_id,
      status: loan.status,
      principal: String(loan.principal),
      due_date: String(loan.due_date),
      investor_id: loan.investor_id,
      seller_id: loan.seller_id,
    });
  } catch (err) {
    callback({ code: 5, message: err.message });
  }
}

/**
 * UpdateLoanStatus — update loan status (DUE, REPAID, OVERDUE).
 */
async function updateLoanStatus(call, callback) {
  try {
    const { loan_id, status } = call.request;
    const loan = await LoanService.updateStatus(loan_id, status);
    callback(null, {
      loan_id: loan.loan_id,
      status: loan.status,
      principal: String(loan.principal),
      due_date: String(loan.due_date),
      investor_id: loan.investor_id,
      seller_id: loan.seller_id,
    });
  } catch (err) {
    callback({ code: 3, message: err.message });
  }
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
