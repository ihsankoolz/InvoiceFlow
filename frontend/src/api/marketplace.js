import api from './axios'

/**
 * Fetch marketplace listings via REST /api/listings (Bidding Orchestrator).
 * @param {object} filters - { urgency, search, sortBy }
 */
export async function fetchListings(filters = {}) {
  const { urgency, search } = filters

  const params = {}
  if (urgency && urgency !== 'ALL') params.urgency_level = urgency
  if (search) params.search = search

  const response = await api.get('/listings', { params })
  return Array.isArray(response.data) ? response.data : []
}

/**
 * Fetch a single listing by id via the marketplace service.
 * @param {string|number} id
 */
export async function fetchListing(id) {
  const response = await api.get(`/listings/${id}`)
  return response.data
}
