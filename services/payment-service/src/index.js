/**
 * Payment Service — Express REST + gRPC server entry point.
 *
 * REST  :5004  — read-only endpoints + Swagger UI at /docs
 * gRPC  :50051 — all financial write operations
 */

const express = require('express');
const cors = require('cors');
const config = require('./config');
const { initDatabase } = require('./database');
const { startGrpcServer } = require('./grpc/server');
const { setupSwagger } = require('./rest/swagger');
const restRoutes = require('./rest/routes');
const { startConsumer } = require('./consumers/eventConsumer');
const { register } = require('./metrics');

const app = express();
app.use(cors());
app.use(express.json());

// Health check
app.get('/health', (_req, res) => {
  res.json({ status: 'ok', service: 'payment-service' });
});

// Prometheus metrics
app.get('/metrics', async (_req, res) => {
  res.set('Content-Type', register.contentType);
  res.end(await register.metrics());
});

// REST routes
app.use('/', restRoutes);

// Swagger UI
setupSwagger(app);

async function main() {
  // 1. Connect to database
  await initDatabase();

  // 2. Start gRPC server
  startGrpcServer(config.grpcPort);

  // 3. Start REST server
  app.listen(config.restPort, '0.0.0.0', () => {
    console.log(`[payment-service] REST server listening on :${config.restPort}`);
    console.log(`[payment-service] Swagger UI at http://localhost:${config.restPort}/docs`);
  });

  // 4. Start RabbitMQ consumer
  try {
    await startConsumer();
  } catch (err) {
    console.error('[payment-service] RabbitMQ consumer failed to start:', err.message);
    console.log('[payment-service] Continuing without RabbitMQ consumer...');
  }
}

main().catch((err) => {
  console.error('[payment-service] Fatal error:', err);
  process.exit(1);
});
