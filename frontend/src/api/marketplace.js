import axios from 'axios'

const TOKEN_KEY = 'invoiceflow_token'

const LISTING_FIELDS = `
  id
  invoice_token
  invoice_id
  seller_id
  face_value
  minimum_bid
  current_bid
  bid_count
  urgency_level
  deadline
  debtor_name
  debtor_uen
  status
  created_at
`

/**
 * Fetch marketplace listings via GraphQL.
 * Uses plain axios (not the api instance) to POST directly to /graphql.
 * @param {object} filters - { urgency, search, sortBy }
 */
export async function fetchListings(filters = {}) {
  const { urgency, search, sortBy } = filters

  // Build a dynamic GraphQL query with optional filter arguments
  const args = []
  if (urgency && urgency !== 'ALL') args.push(`urgency_level: "${urgency}"`)
  if (search) args.push(`search: "${search}"`)
  if (sortBy) args.push(`sort_by: "${sortBy}"`)

  const argString = args.length ? `(${args.join(', ')})` : ''

  const query = `
    query {
      listings${argString} {
        ${LISTING_FIELDS}
      }
    }
  `

  const token = localStorage.getItem(TOKEN_KEY)
  const headers = token ? { Authorization: `Bearer ${token}` } : {}

  const response = await axios.post(
    '/graphql',
    { query },
    { headers }
  )

  if (response.data.errors) {
    throw new Error(response.data.errors[0]?.message || 'GraphQL error')
  }

  return response.data.data.listings
}

/**
 * Fetch a single listing by id.
 * @param {string|number} id
 */
export async function fetchListing(id) {
  const query = `
    query {
      listing(id: ${id}) {
        ${LISTING_FIELDS}
      }
    }
  `

  const token = localStorage.getItem(TOKEN_KEY)
  const headers = token ? { Authorization: `Bearer ${token}` } : {}

  const response = await axios.post(
    '/graphql',
    { query },
    { headers }
  )

  if (response.data.errors) {
    throw new Error(response.data.errors[0]?.message || 'GraphQL error')
  }

  return response.data.data.listing
}
