import api from './axios'

/**
 * Execute a GraphQL query against the bidding orchestrator's /api/graphql endpoint.
 * Reuses the same axios instance so the JWT Authorization header is attached automatically.
 *
 * @param {string} query     - GraphQL query string
 * @param {object} variables - Query variables
 * @returns {Promise<object>} - The `data` field of the GraphQL response
 */
export async function gqlQuery(query, variables = {}) {
  const response = await api.post('/graphql', { query, variables })
  if (response.data.errors?.length) {
    throw new Error(response.data.errors[0].message)
  }
  return response.data.data
}
