/**
 * Payment Service Configuration
 * Loads environment variables with sensible defaults.
 */

require('dotenv').config();

const config = {
  /** MySQL connection string */
  dbUrl: process.env.DB_URL || 'mysql://root:password@localhost:3310/payment_db',

  /** gRPC server port */
  grpcPort: parseInt(process.env.GRPC_PORT, 10) || 50051,

  /** REST / Express server port */
  restPort: parseInt(process.env.REST_PORT, 10) || 5004,

  /** RabbitMQ connection URL */
  rabbitmqUrl: process.env.RABBITMQ_URL || 'amqp://guest:guest@localhost:5672',

  /** Node environment */
  nodeEnv: process.env.NODE_ENV || 'development',
};

module.exports = config;
