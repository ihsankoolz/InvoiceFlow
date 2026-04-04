const client = require('prom-client');

const register = new client.Registry();
client.collectDefaultMetrics({ register });

const grpcOpsTotal = new client.Counter({
  name: 'payment_grpc_operations_total',
  help: 'Total gRPC operations by method and status',
  labelNames: ['method', 'status'],
  registers: [register],
});

const grpcDuration = new client.Histogram({
  name: 'payment_grpc_duration_seconds',
  help: 'gRPC operation duration in seconds',
  labelNames: ['method'],
  buckets: [0.01, 0.05, 0.1, 0.5, 1, 2],
  registers: [register],
});

module.exports = { register, grpcOpsTotal, grpcDuration };
