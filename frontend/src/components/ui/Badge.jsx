/**
 * Badge component for invoice/bid statuses and urgency levels.
 * Matches the InvoiceFlow design system.
 */

const STATUS_STYLES = {
  // Invoice / bid statuses
  DRAFT:     'bg-gray-100 text-gray-600 border border-gray-300',
  LISTED:    'bg-[#e6f0ef] text-teal border border-teal/30',
  ACTIVE:    'bg-[#e6f0ef] text-teal border border-teal/30',
  FINANCED:  'bg-[#e8f5e0] text-[#3e9b00] border border-[#3e9b00]/30',
  ACCEPTED:  'bg-[#e8f5e0] text-[#3e9b00] border border-[#3e9b00]/30',
  REPAID:    'bg-[#d4edda] text-[#1a6b2f] border border-[#1a6b2f]/30',
  DEFAULTED: 'bg-red-50 text-red-700 border border-red-300',
  REJECTED:  'bg-red-50 text-red-700 border border-red-300',
  OVERDUE:   'bg-red-50 text-red-700 border border-red-300',
  PENDING:   'bg-yellow-50 text-yellow-700 border border-yellow-300',
  DUE:       'bg-[#fff3e0] text-[#ff9500] border border-[#ff9500]/40',

  // Urgency levels
  LOW:      'bg-[#e8f5e0] text-[#3e9b00] border border-[#3e9b00]/30',
  MEDIUM:   'bg-yellow-50 text-yellow-700 border border-yellow-300',
  HIGH:     'bg-[#fff3e0] text-[#ff9500] border border-[#ff9500]/40',
  CRITICAL: 'bg-red-50 text-red-700 border border-red-300',
}

const DEFAULT_STYLE = 'bg-gray-100 text-gray-600 border border-gray-300'

/**
 * @param {string} status - One of the known status/urgency strings
 * @param {string} [className] - Additional Tailwind classes
 */
export default function Badge({ status, className = '' }) {
  const style = STATUS_STYLES[status?.toUpperCase()] || DEFAULT_STYLE
  return (
    <span
      className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-['Lato'] font-semibold ${style} ${className}`}
    >
      {status}
    </span>
  )
}
