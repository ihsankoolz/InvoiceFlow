/**
 * Manual JWT decoder — no external library required.
 */

/**
 * Decode a JWT token and return the payload as an object.
 * Returns null if the token is invalid or malformed.
 */
export function decodeJWT(token) {
  if (!token) return null
  try {
    const parts = token.split('.')
    if (parts.length !== 3) return null
    // Base64url → Base64 → decode
    const base64 = parts[1].replace(/-/g, '+').replace(/_/g, '/')
    const padded = base64.padEnd(base64.length + ((4 - (base64.length % 4)) % 4), '=')
    const jsonStr = atob(padded)
    return JSON.parse(jsonStr)
  } catch {
    return null
  }
}

/**
 * Returns true if the token is expired (or invalid).
 * Checks the `exp` field in the JWT payload (Unix timestamp in seconds).
 */
export function isTokenExpired(token) {
  const payload = decodeJWT(token)
  if (!payload || typeof payload.exp !== 'number') return true
  // exp is seconds since epoch; Date.now() is milliseconds
  return Date.now() >= payload.exp * 1000
}
