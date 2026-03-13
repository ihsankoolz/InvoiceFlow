/**
 * gRPC server setup for Payment Service.
 * Loads payment.proto and registers all RPC handlers.
 */

const grpc = require('@grpc/grpc-js');
const protoLoader = require('@grpc/proto-loader');
const path = require('path');
const handlers = require('./handlers');

const PROTO_PATH = path.join(__dirname, '..', '..', 'proto', 'payment.proto');

const packageDefinition = protoLoader.loadSync(PROTO_PATH, {
  keepCase: true,
  longs: String,
  enums: String,
  defaults: true,
  oneofs: true,
});

const paymentProto = grpc.loadPackageDefinition(packageDefinition).payment;

/**
 * Start the gRPC server on the given port.
 * @param {number} port
 */
function startGrpcServer(port) {
  const server = new grpc.Server();

  server.addService(paymentProto.PaymentService.service, {
    LockEscrow: handlers.lockEscrow,
    ReleaseEscrow: handlers.releaseEscrow,
    ConvertEscrowToLoan: handlers.convertEscrowToLoan,
    CreateLoan: handlers.createLoan,
    ReleaseFundsToSeller: handlers.releaseFundsToSeller,
    CreditWallet: handlers.creditWallet,
    GetLoan: handlers.getLoan,
    UpdateLoanStatus: handlers.updateLoanStatus,
  });

  server.bindAsync(
    `0.0.0.0:${port}`,
    grpc.ServerCredentials.createInsecure(),
    (err, boundPort) => {
      if (err) {
        console.error('[payment-service] gRPC server failed to bind:', err);
        return;
      }
      console.log(`[payment-service] gRPC server listening on :${boundPort}`);
    },
  );
}

module.exports = { startGrpcServer };
