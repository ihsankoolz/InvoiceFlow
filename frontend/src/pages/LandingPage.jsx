import { Link } from 'react-router-dom'
import imgAsterisk from '../assets/svgs/hero/Asterisk1.svg'
import imgSpiral from '../assets/svgs/hero/OrangeSpiral.svg'
import imgOrangeDiamond from '../assets/svgs/hero/OrangeHollowDiamond.svg'
import imgPurpleDiamond from '../assets/svgs/hero/PurpleDiamond.svg'
import imgArrow from '../assets/svgs/hero/RedirectArrow.svg'
import hiwPurpleArrow from '../assets/svgs/how_it_works/PurpleArrow.svg'
import hiwBlackArrow from '../assets/svgs/how_it_works/BlackArrow.svg'
import hiwOrangeDiamond from '../assets/svgs/how_it_works/OrangeDiamond.svg'
import featPurpleDiamond from '../assets/svgs/features/PurpleDiamond.svg'
import featAsterisk from '../assets/svgs/features/Asterisk2.svg'
import featOrangeSpiral from '../assets/svgs/features/OrangeSpiral.svg'
import forPurpleArrow from '../assets/svgs/for/PurpleArrow.svg'
import forOrangeDiamond from '../assets/svgs/for/OrangeHollowDiamond.svg'
import teamAsterisk1 from '../assets/svgs/our_team/Asterisk1.svg'
import teamAsterisk2 from '../assets/svgs/our_team/Asterisk2.svg'
import teamPurpleSpiral from '../assets/svgs/our_team/PurpleSpiral.svg'


function TimerIcon() {
  return (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#222" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="12" cy="12" r="10"/>
      <polyline points="12 6 12 12 16 14"/>
    </svg>
  )
}

const FEATURES = [
  {
    num: '01',
    title: 'Anti-snipe Protection',
    desc: 'Last-minute bids automatically extend the auction window, giving all investors a fair chance to respond.',
  },
  {
    num: '02',
    title: 'ACRA UEN Validation',
    desc: "Every debtor is validated against Singapore's company registry before a listing goes live.",
  },
  {
    num: '03',
    title: 'Escrow-secured Bids',
    desc: 'Investor funds are locked in escrow on bid and released instantly if they are outbid.',
  },
  {
    num: '04',
    title: 'PDF Auto-extraction',
    desc: 'Upload your invoice PDF and key fields are extracted automatically — edit before submitting.',
  },
  {
    num: '05',
    title: 'Real-time Notification',
    desc: 'WebSocket push alerts for outbid events, auction closes, loan updates, and repayments.',
  },
  {
    num: '06',
    title: 'Stripe Payments',
    desc: 'Wallet top-ups and loan repayments handled via Stripe — secure, fast, and auditable.',
  },
]

const HOW_IT_WORKS = [
  'Small Business submits an invoice onto InvoiceFlow',
  'Invoice goes live on the marketplace',
  'An Investor purchases the invoice on the marketplace (via bidding)',
  'Big business eventually pays the smaller firm',
  'Smaller firm pays the Investor the invoice value',
]

const TEAM = [
  { name: 'Keene' },
  { name: 'Ihsan' },
  { name: 'Amanda' },
  { name: 'Gyaltsen' },
  { name: 'Michelle' },
  { name: 'Cheng Lin' },
]

function InvoiceCard({ rotateClass }) {
  return (
    <div className={`bg-white border border-[rgba(34,34,34,0.22)] rounded-[10px] shadow-[0px_2px_2px_0px_rgba(34,34,34,0.22)] w-[262px] overflow-hidden ${rotateClass}`}>
      {/* Top row */}
      <div className="relative px-4 pt-4 pb-2">
        <span className="bg-[#ff9500] text-white text-xs font-['Lato'] font-medium px-3 py-1 rounded-[7px]">
          Ending soon
        </span>
        <div className="absolute right-4 top-4 text-right">
          <div className="flex items-center justify-end gap-1 text-xs text-ink">
            <TimerIcon />
            <span className="font-['Lato'] text-sm">2h 14m</span>
          </div>
        </div>
      </div>

      {/* Invoice ID */}
      <div className="px-4 pb-1">
        <p className="font-['Lato'] text-xs text-ink">INV-2016-001</p>
      </div>

      {/* Bid info */}
      <div className="px-4 pb-3 flex justify-between items-end">
        <div>
          <p className="font-['Lato'] text-sm text-ink">Current bid</p>
          <p className="font-['Lato'] text-xs font-medium text-[#3e9b00]">+11.1% return</p>
        </div>
        <p className="font-['Lato'] font-bold text-2xl text-ink">$9000</p>
      </div>

      {/* Divider */}
      <div className="mx-4 h-px bg-[rgba(34,34,34,0.8)]" />

      {/* Face value / Min bid */}
      <div className="px-4 py-2 space-y-1">
        <div className="flex gap-4 text-xs font-['Lato'] text-ink">
          <span className="w-20">Face value</span>
          <span>$10000</span>
        </div>
        <div className="flex gap-4 text-xs font-['Lato'] text-ink">
          <span className="w-20">Min bid</span>
          <span>$8500</span>
        </div>
      </div>

      {/* Divider */}
      <div className="mx-4 h-px bg-[rgba(34,34,34,0.8)]" />

      {/* Debtor */}
      <div className="px-4 py-2 space-y-0.5">
        <div className="flex gap-4 text-xs font-['Lato'] text-ink">
          <span className="w-20">Debtor</span>
          <span className="flex-1">Meridian Tech Solutions</span>
        </div>
        <div className="flex gap-4 text-xs font-['Lato'] text-ink">
          <span className="w-20"></span>
          <span>202056789A</span>
        </div>
      </div>

      {/* CTA */}
      <div className="px-4 pb-4 pt-2">
        <button className="w-full bg-ink text-white rounded-[10px] py-3 font-['Lato'] font-medium text-sm">
          Place bid
        </button>
      </div>
    </div>
  )
}

function ArrowCTA({ children, to = '#' }) {
  return (
    <Link to={to} className="flex items-center gap-3 group">
      <img src={imgArrow} alt="" aria-hidden="true" className="w-7 h-7 group-hover:translate-x-0.5 transition-transform" />
      <span className="font-['Lato'] text-lg text-ink">{children}</span>
    </Link>
  )
}

export default function LandingPage() {
  return (
    <div className="relative bg-cream min-h-screen">

      {/* ─── Ombre blob ──────────────────────────────────────────── */}
      <div
        aria-hidden="true"
        className="pointer-events-none select-none absolute -top-40 -left-40 w-[700px] h-[700px]"
        style={{ background: 'radial-gradient(circle at top left, rgba(255,149,0,0.75) 0%, rgba(255,149,0,0.35) 40%, transparent 65%)', zIndex: 0 }}
      />

      {/* ─── Navbar ─────────────────────────────────────────────── */}
      <nav className="relative flex items-center justify-between px-16 py-6 border-b border-transparent whitespace-nowrap" style={{ zIndex: 2 }}>
        <span className="font-['Lato'] font-bold text-[22px] text-ink">InvoiceFlow</span>
        <div className="flex items-center gap-8">
          <Link to="/login" className="font-['Lato'] font-bold text-base text-ink">
            Sign In
          </Link>
          <Link
            to="/register"
            className="bg-ink text-white font-['Lato'] font-semibold text-base px-7 py-2.5 rounded-lg hover:bg-[#333] transition-colors"
          >
            Get Started
          </Link>
        </div>
      </nav>

      {/* ─── Hero ────────────────────────────────────────────────── */}
      <section className="relative px-16 pt-16 pb-24 max-w-[1440px] mx-auto">
        {/* Spiral — top right */}
        <img src={imgSpiral} alt="" aria-hidden="true" className="absolute top-4 left-[60%] pointer-events-none select-none" />
        {/* Orange hollow diamond — top left of heading */}
        <img src={imgOrangeDiamond} alt="" aria-hidden="true" className="absolute top-12 left-12 pointer-events-none select-none" style={{ width: 22 }} />

        <div className="relative" style={{ zIndex: 1 }}>
          <h1 className="font-display font-semibold text-[52px] leading-tight text-ink mb-2 max-w-[700px]">
            A Smarter Marketplace for Invoice Financing
            {/* Purple diamond inline after heading */}
            <img src={imgPurpleDiamond} alt="" aria-hidden="true" className="inline-block ml-3 mb-1 pointer-events-none select-none" style={{ width: 22, verticalAlign: 'middle' }} />
          </h1>
          {/* Asterisk — below heading */}
          <div className="mb-4">
            <img src={imgAsterisk} alt="" aria-hidden="true" className="pointer-events-none select-none" style={{ width: 12 }} />
          </div>
          <p className="font-['Lato'] text-lg text-ink leading-relaxed mb-8 max-w-[560px]">
            InvoiceFlow is a digital invoice-financing platform where businesses sell unpaid invoices to investors
            in exchange for immediate cash, while investors earn short-term returns.
          </p>
          <div className="flex flex-col gap-4">
            <ArrowCTA to="/invoices/new">List an Invoice</ArrowCTA>
            <ArrowCTA to="/marketplace">View marketplace</ArrowCTA>
          </div>
        </div>
      </section>

      {/* ─── How it works ────────────────────────────────────────── */}
      <section className="relative pt-8 pb-24 max-w-[1440px] mx-auto px-16">
        <div className="grid grid-cols-2 gap-24 items-start">
          {/* Left: decorative invoice cards */}
          <div className="relative h-[480px] hidden lg:block">
            <div className="absolute top-4 left-16 -rotate-[5deg]">
              <InvoiceCard rotateClass="" />
            </div>
            <div className="absolute top-32 left-44 rotate-[10deg]">
              <InvoiceCard rotateClass="" />
            </div>
          </div>

          {/* Right: steps */}
          <div className="relative">
            {/* Purple arrow — top-left, above heading */}
            <img src={hiwPurpleArrow} alt="" aria-hidden="true" className="absolute -top-10 pointer-events-none select-none w-16" style={{ left: 'calc(-1.5rem + 10px)' }} />
            <h2 className="font-display font-semibold text-[40px] text-ink text-center mb-8">
              How it works
            </h2>
            {/* Black arrow — right of heading */}
            <img src={hiwBlackArrow} alt="" aria-hidden="true" className="absolute top-2 pointer-events-none select-none w-12" style={{ right: 'calc(-1.5rem + 10px)' }} />
            <div className="space-y-0 w-full">
              {HOW_IT_WORKS.map((step, i) => (
                <div key={i} className={`flex items-center gap-6 h-[48px] w-full ${i < HOW_IT_WORKS.length - 1 ? 'border-b border-ink/80' : ''}`}>
                  <span className="font-['Lato'] font-bold text-base text-ink shrink-0">0{i + 1}</span>
                  <span className="font-['Lato'] text-base text-ink">{step}</span>
                </div>
              ))}
            </div>
            {/* Orange diamond — below last step, centered */}
            <div className="flex justify-end mt-6" style={{ paddingRight: '40px' }}>
              <img src={hiwOrangeDiamond} alt="" aria-hidden="true" className="pointer-events-none select-none w-5" />
            </div>
          </div>
        </div>
      </section>

      {/* ─── Features ────────────────────────────────────────────── */}
      <section className="relative pt-8 pb-24 max-w-[1440px] mx-auto px-16">
        <h2 className="font-display font-semibold text-[40px] text-ink text-center mb-12">
          Features
        </h2>
        {/* Purple diamond — top left above grid */}
        <img src={featPurpleDiamond} alt="" aria-hidden="true" className="absolute top-20 left-40 pointer-events-none select-none w-6" />
        <div className="relative grid grid-cols-3 gap-6 max-w-[900px] mx-auto">
          {FEATURES.map((f) => (
            <div
              key={f.num}
              className="bg-white border border-ink rounded-[20px] p-8 overflow-hidden"
            >
              <p className="font-['Lato'] text-base text-ink mb-3">{f.num}</p>
              <p className="font-['Lato'] font-bold text-lg text-ink mb-3">{f.title}</p>
              <p className="font-['Lato'] font-light text-sm text-ink leading-relaxed">{f.desc}</p>
            </div>
          ))}
          {/* Asterisk — right side between rows */}
          <img src={featAsterisk} alt="" aria-hidden="true" className="absolute -right-12 top-[45%] pointer-events-none select-none w-6" />
        </div>
        {/* Orange spiral — bottom left below grid */}
        <img src={featOrangeSpiral} alt="" aria-hidden="true" className="absolute bottom-10 left-36 pointer-events-none select-none w-16" />
      </section>

      {/* ─── For Businesses / For Investors ──────────────────────── */}
      <section className="relative py-24 max-w-[1440px] mx-auto px-16">
        {/* Purple arrow — top right */}
        <img src={forPurpleArrow} alt="" aria-hidden="true" className="absolute top-16 right-10 pointer-events-none select-none w-14" />
        {/* Orange hollow diamond — bottom left */}
        <img src={forOrangeDiamond} alt="" aria-hidden="true" className="absolute -bottom-1 left-96 pointer-events-none select-none w-5" />
        <div className="grid grid-cols-2 divide-x divide-ink/20 gap-0">
          {/* For Businesses */}
          <div className="pr-16 flex flex-col h-full">
            <p className="font-['Lato'] text-xl text-ink mb-4">For Businesses</p>
            <h3 className="font-['Lato'] font-semibold text-[32px] text-ink leading-tight mb-6">
              Stop waiting 90 days to get paid.
            </h3>
            <p className="font-['Lato'] text-base text-ink leading-relaxed mb-8">
              Your invoice, your terms. You control the auction. Set a minimum bid to protect your margin and choose
              how long it runs. Capital lands in your account the same day it closes.
            </p>
            <div className="mt-auto"><ArrowCTA to="/register">Get Started</ArrowCTA></div>
          </div>

          {/* For Investors */}
          <div className="pl-16 flex flex-col h-full">
            <p className="font-['Lato'] text-xl text-ink mb-4">For Investors</p>
            <h3 className="font-['Lato'] font-semibold text-[32px] text-ink leading-tight mb-6">
              Short-duration assets.
              <br />
              Verified debtors.
            </h3>
            <p className="font-['Lato'] text-base text-ink leading-relaxed mb-8">
              Filter listings by urgency level to find motivated sellers offering better discounts. Every listing
              shows minimum bid upfront.
            </p>
            <div className="mt-auto"><ArrowCTA to="/register">Start Investing</ArrowCTA></div>
          </div>
        </div>
      </section>

      {/* ─── Our Team ────────────────────────────────────────────── */}
      <section className="relative py-24 max-w-[1440px] mx-auto px-16">

        <h2 className="font-display font-semibold text-[40px] text-ink text-center mb-12">
          Our Team
        </h2>
        {/* Asterisk1 — right side, slightly higher than rightmost circle */}
        <img src={teamAsterisk1} alt="" aria-hidden="true" className="absolute top-[20%] right-40 pointer-events-none select-none w-4" />
        {/* Asterisk2 — left side, slightly below Keene */}
        <img src={teamAsterisk2} alt="" aria-hidden="true" className="absolute top-[52%] left-40 pointer-events-none select-none w-6" />
        <div className="grid grid-cols-3 gap-y-12 gap-x-12 max-w-[900px] mx-auto">
          {TEAM.map((member) => (
            <div key={member.name} className="flex flex-col items-center gap-4">
              <div className="w-[220px] h-[220px] rounded-full bg-white border border-ink" />
              <p className="font-['Lato'] text-lg text-ink text-center">{member.name}</p>
            </div>
          ))}
        </div>
        {/* Purple spiral — bottom right */}
        <img src={teamPurpleSpiral} alt="" aria-hidden="true" className="absolute bottom-16 right-40 pointer-events-none select-none w-12" />
      </section>

      {/* ─── Footer ──────────────────────────────────────────────── */}
      <footer className="border-t border-ink/10 py-10 px-16 text-center">
        <p className="font-['Lato'] text-base text-ink/50">
          © 2026 InvoiceFlow · SMU IS213 Enterprise Solution Development
        </p>
      </footer>
    </div>
  )
}
