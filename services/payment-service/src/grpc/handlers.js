/**
 * gRPC method handlers for PaymentService.
 * Each handler receives (call, callback) and delegates to the appropriate service class.
 *
 * See BUILD_INSTRUCTIONS_V2.md Section 5 — gRPC Service Definition
 */

const WalletService = require('../services/WalletService');
const EscrowService = require('../services/EscrowService');
const LoanService = require('../services/LoanService');
const { grpcOpsTotal, grpcDuration } = require('../metrics');

/**
 * LockEscrow — debit investor wallet, create escrow record.
 */
async function lockEscrow(call, callback) {
  const end = grpcDuration.startTimer({ method: 'lockEscrow' });
  try {
    const { investor_id, invoice_token, amount, idempotency_key } = call.request;
    const escrow = await EscrowService.lockEscrow(investor_id, invoice_token, amount, idempotency_key);
    grpcOpsTotal.inc({ method: 'lockEscrow', status: 'success' });
    callback(null, { id: String(escrow.id), status: escrow.status, amount: String(escrow.amount) });
  } catch (err) {
    grpcOpsTotal.inc({ method: 'lockEscrow', status: 'error' });
    callback({ code: 3, message: err.message });
  } finally {
    end();
  }
}

/**
 * ReleaseEscrow — return escrowed funds to investor wallet, mark RELEASED.
 */
async function releaseEscrow(call, callback) {
  const end = grpcDuration.startTimer({ method: 'releaseEscrow' });
  try {
    const { investor_id, invoice_token, idempotency_key } = call.request;
    const escrow = await EscrowService.releaseEscrow(investor_id, invoice_token, idempotency_key);
    grpcOpsTotal.inc({ method: 'releaseEscrow', status: 'success' });
    callback(null, { id: String(escrow.id), status: escrow.status, amount: String(escrow.amount) });
  } catch (err) {
    grpcOpsTotal.inc({ method: 'releaseEscrow', status: 'error' });
    callback({ code: 5, message: err.message });
  } finally {
    end();
  }
}

/**
 * ConvertEscrowToLoan — mark escrow CONVERTED (funds stay in system for loan).
 */
async function convertEscrowToLoan(call, callback) {
  const end = grpcDuration.startTimer({ method: 'convertEscrowToLoan' });
  try {
    const { investor_id, invoice_token, idempotency_key } = call.request;
    const escrow = await EscrowService.convertToLoan(investor_id, invoice_token, idempotency_key);
    grpcOpsTotal.inc({ method: 'convertEscrowToLoan', status: 'success' });
    callback(null, { id: String(escrow.id), status: escrow.status, amount: String(escrow.amount) });
  } catch (err) {
    grpcOpsTotal.inc({ method: 'convertEscrowToLoan', status: 'error' });
    callback({ code: 5, message: err.message });
  } finally {
    end();
  }
}

/**
 * CreateLoan — create a new loan record.
 */
async function createLoan(call, callback) {
  const end = grpcDuration.startTimer({ method: 'createLoan' });
  try {
    const { invoice_token, investor_id, seller_id, principal, bid_amount, due_date, idempotency_key } = call.request;
    const loan = await LoanService.createLoan(
      { invoice_token, investor_id, seller_id, principal, bid_amount, due_date },
      idempotency_key,
    );
    grpcOpsTotal.inc({ method: 'createLoan', status: 'success' });
    callback(null, {
      loan_id: loan.loan_id,
      status: loan.status,
      principal: String(loan.principal),
      bid_amount: String(loan.bid_amount),
      due_date: new Date(loan.due_date).toISOString(),
      investor_id: loan.investor_id,
      seller_id: loan.seller_id,
      invoice_token: loan.invoice_token || '',
      grace_end: loan.grace_end ? new Date(loan.grace_end).toISOString() : '',
    });
  } catch (err) {
    grpcOpsTotal.inc({ method: 'createLoan', status: 'error' });
    callback({ code: 3, message: err.message });
  } finally {
    end();
  }
}

/**
 * ReleaseFundsToSeller — credit seller wallet with loan principal.
 */
async function releaseFundsToSeller(call, callback) {
  const end = grpcDuration.startTimer({ method: 'releaseFundsToSeller' });
  try {
    const { seller_id, amount, idempotency_key } = call.request;
    const result = await LoanService.releaseFundsToSeller(seller_id, amount, idempotency_key);
    grpcOpsTotal.inc({ method: 'releaseFundsToSeller', status: 'success' });
    callback(null, { success: result.success, message: result.message });
  } catch (err) {
    grpcOpsTotal.inc({ method: 'releaseFundsToSeller', status: 'error' });
    callback({ code: 3, message: err.message });
  } finally {
    end();
  }
}

/**
 * CreditWallet — add funds to a user wallet (Stripe top-up or escrow release).
 */
async function creditWallet(call, callback) {
  const end = grpcDuration.startTimer({ method: 'creditWallet' });
  try {
    const { user_id, amount } = call.request;
    const wallet = await WalletService.creditWallet(user_id, amount);
    grpcOpsTotal.inc({ method: 'creditWallet', status: 'success' });
    callback(null, { user_id: wallet.user_id, balance: String(wallet.balance) });
  } catch (err) {
    grpcOpsTotal.inc({ method: 'creditWallet', status: 'error' });
    callback({ code: 3, message: err.message });
  } finally {
    end();
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
      due_date: new Date(loan.due_date).toISOString(),
      investor_id: loan.investor_id,
      seller_id: loan.seller_id,
      invoice_token: loan.invoice_token || '',
      grace_end: loan.grace_end ? new Date(loan.grace_end).toISOString() : '',
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
    const { loan_id, status, grace_end } = call.request;
    const loan = await LoanService.updateStatus(loan_id, status, grace_end || null);
    callback(null, {
      loan_id: loan.loan_id,
      status: loan.status,
      principal: String(loan.principal),
      due_date: new Date(loan.due_date).toISOString(),
      investor_id: loan.investor_id,
      seller_id: loan.seller_id,
      invoice_token: loan.invoice_token || '',
      grace_end: loan.grace_end ? new Date(loan.grace_end).toISOString() : '',
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
