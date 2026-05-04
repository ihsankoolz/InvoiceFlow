/**
 * Sequelize database connection for the Payment Service.
 */

const { Sequelize } = require('sequelize');
const config = require('./config');

const sequelize = new Sequelize(config.dbUrl, {
  dialect: 'mysql',
  logging: config.nodeEnv === 'development' ? console.log : false,
  pool: {
    max: 10,
    min: 0,
    acquire: 30000,
    idle: 10000,
  },
});

/**
 * Test the database connection and sync models.
 * @returns {Promise<void>}
 */
async function initDatabase() {
  try {
    await sequelize.authenticate();
    console.log('[payment-service] Database connection established.');
    await sequelize.sync();
    console.log('[payment-service] Models synchronised.');
  } catch (err) {
    console.error('[payment-service] Unable to connect to database:', err.message);
    throw err;
  }
}

module.exports = { sequelize, initDatabase };
