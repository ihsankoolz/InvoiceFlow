/**
 * Swagger UI setup for Payment Service REST endpoints.
 */

const swaggerJsdoc = require('swagger-jsdoc');
const swaggerUi = require('swagger-ui-express');

const options = {
  definition: {
    openapi: '3.0.0',
    info: {
      title: 'Payment Service',
      version: '1.0.0',
      description:
        'Handles all financial operations: wallets, escrow, loans. ' +
        'REST for reads, gRPC for writes (see payment.proto).',
    },
    servers: [{ url: 'http://localhost:5004' }],
    paths: {
      '/health': {
        get: {
          tags: ['Health'],
          summary: 'Health check',
          responses: { 200: { description: 'Service is healthy' } },
        },
      },
      '/wallets/{userId}': {
        get: {
          tags: ['Wallets'],
          summary: 'Get wallet balance',
          parameters: [
            { name: 'userId', in: 'path', required: true, schema: { type: 'integer' } },
          ],
          responses: { 200: { description: 'Wallet details' } },
        },
      },
      '/loans/{loanId}': {
        get: {
          tags: ['Loans'],
          summary: 'Get loan details',
          parameters: [
            { name: 'loanId', in: 'path', required: true, schema: { type: 'string' } },
          ],
          responses: { 200: { description: 'Loan details' } },
        },
      },
      '/loans': {
        get: {
          tags: ['Loans'],
          summary: 'Get loans by investor',
          parameters: [
            { name: 'investor_id', in: 'query', required: true, schema: { type: 'integer' } },
          ],
          responses: { 200: { description: 'List of loans' } },
        },
      },
      '/escrows': {
        get: {
          tags: ['Escrows'],
          summary: 'Get active escrows for an investor',
          parameters: [
            { name: 'investor_id', in: 'query', required: true, schema: { type: 'integer' } },
          ],
          responses: { 200: { description: 'List of escrows' } },
        },
      },
    },
  },
  apis: [],
};

const swaggerSpec = swaggerJsdoc(options);

function setupSwagger(app) {
  app.use('/docs', swaggerUi.serve, swaggerUi.setup(swaggerSpec));
}

module.exports = { setupSwagger };
