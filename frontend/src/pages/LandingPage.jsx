import { useState, useEffect, useRef } from 'react'
import { Link } from 'react-router-dom'
import { ChevronDown } from 'lucide-react'
import PublicNav from '../components/layout/PublicNav'

import imgBusiness  from '../assets/images/image 5.png'
import imgStripe    from '../assets/images/image 7.png'
import imgAcra      from '../assets/images/image 9.png'
import imgInvestor  from '../assets/images/image 10.png'
import imgIphone    from '../assets/images/Blue.png'
import iconArrow    from '../assets/icons/7.svg'

/* ── Animation helpers ── */
function useInView(threshold = 0.08) {
  const ref = useRef(null)
  const [inView, setInView] = useState(false)
  useEffect(() => {
    const el = ref.current
    if (!el) return
    const obs = new IntersectionObserver(
      ([entry]) => { if (entry.isIntersecting) { setInView(true); obs.disconnect() } },
      { threshold }
    )
    obs.observe(el)
    return () => obs.disconnect()
  }, [threshold])
  return [ref, inView]
}

function fadeUp(visible, delay = 0) {
  if (visible) return { animation: 'landFadeUp 600ms ease both', animationDelay: `${delay}ms` }
  return { opacity: 0, transform: 'translateY(24px)' }
}

/* ── FAQ Accordion item ── */
function FAQItem({ question, answer }) {
  const [open, setOpen] = useState(false)
  return (
    <div className="border-b border-[#1c3f3a]/10 last:border-0">
      <button
        onClick={() => setOpen(o => !o)}
        className="w-full flex items-center justify-between px-6 py-5 text-left"
      >
        <span className="font-['Lato'] font-medium text-black text-xl">{question}</span>
        <ChevronDown
          size={20}
          className="text-black flex-shrink-0 transition-transform duration-200"
          style={{ transform: open ? 'rotate(180deg)' : 'rotate(0deg)' }}
        />
      </button>
      {open && (
        <p className="px-6 pb-5 font-['Lato'] text-black text-base leading-relaxed">
          {answer}
        </p>
      )}
    </div>
  )
}

const BUSINESS_FAQS = [
  { question: 'How do I get paid through InvoiceFlow?', answer: 'Once your invoice is verified and listed, investors bid in a live auction. The winning bid amount is transferred directly to your InvoiceFlow wallet the same day the auction closes.' },
  { question: 'How fast can I receive funds?', answer: 'Funds are released to your wallet the same day the auction closes. Once in your wallet, you can withdraw immediately.' },
  { question: 'What happens if no one bids on my invoice?', answer: 'If the auction closes with no bids, the invoice remains in your account and you can relist it at any time with adjusted terms.' },
]
const INVESTOR_FAQS = [
  { question: 'How do I start bidding on invoices?', answer: 'Top up your wallet via Stripe, browse the marketplace, and place bids on any active listing. The highest bid at auction close wins.' },
  { question: 'How are returns calculated?', answer: 'Your return is the difference between the face value of the invoice and your winning bid amount, expressed as a percentage of your bid.' },
  { question: 'What happens if a business defaults?', answer: 'If a business fails to repay within the grace period, the invoice is marked as defaulted and the platform initiates recovery proceedings. Investors are notified immediately.' },
]

const BUSINESS_STEPS = [
  { num: '01', title: 'Upload your Invoice',       body: 'Upload your invoice PDF. Review and confirm before going live.' },
  { num: '02', title: 'Verification',              body: "Your debtor's UEN is checked against Singapore's ACRA registry. Once verified, your invoice is listed with the minimum bid and auction timing you set." },
  { num: '03', title: 'Investors bid, you get funded', body: 'Investors compete in a live auction. When it closes, the winning bid becomes a short-term loan and funds are released to your wallet the same day.' },
  { num: '04', title: 'Repay when your debtor pays',  body: 'Once your debtor settles the invoice, you repay through the platform via Stripe. Repay on time and your account stays active for future listings.' },
]
const INVESTOR_STEPS = [
  { num: '01', title: 'Top up your wallet',   body: 'Add funds to your InvoiceFlow wallet quickly and securely through Stripe.' },
  { num: '02', title: 'Browse the marketplace', body: 'Filter listings by urgency, face value, or deadline. Every listing shows the debtor, minimum bid, and auction countdown upfront.' },
  { num: '03', title: 'Place your bid',       body: 'Bid on verified invoices. Anti-snipe protection ensures fair auctions — any bid in the final 5 minutes extends the deadline.' },
  { num: '04', title: 'Earn your return',     body: 'When you win, funds are escrowed until the auction closes. Returns are credited to your wallet once the business repays.' },
]

const TEAM = ['Keene', 'Ihsan', 'Amanda', 'Gyaltsen', 'Michelle', 'Cheng Lin']

export default function LandingPage() {
  const [howTab, setHowTab] = useState('business')
  const [faqTab, setFaqTab] = useState('business')

  const [heroRef,  heroIn]  = useInView(0.05)
  const [bentoRef, bentoIn] = useInView(0.05)
  const [valueRef, valueIn] = useInView(0.05)
  const [howRef,   howIn]   = useInView(0.05)
  const [faqRef,   faqIn]   = useInView(0.05)
  const [teamRef,  teamIn]  = useInView(0.05)

  const howSteps = howTab === 'business' ? BUSINESS_STEPS : INVESTOR_STEPS
  const faqItems = faqTab === 'business' ? BUSINESS_FAQS  : INVESTOR_FAQS

  return (
    <div className="bg-white font-['Lato'] min-h-screen">
      <style>{`
        @keyframes landFadeUp {
          from { opacity: 0; transform: translateY(24px); }
          to   { opacity: 1; transform: translateY(0); }
        }
        @keyframes landFadeIn {
          from { opacity: 0; }
          to   { opacity: 1; }
        }
        .bento-card {
          transition: transform 300ms cubic-bezier(0.34,1.56,0.64,1), box-shadow 300ms ease;
        }
        .bento-card:hover {
          transform: scale(1.025);
          box-shadow: 0 8px 24px rgba(0,0,0,0.07);
          z-index: 1;
        }
      `}</style>

      <PublicNav />

      {/* ── HERO ── */}
      <section
        ref={heroRef}
        className="px-8 lg:px-16 flex items-center justify-between gap-12 max-w-[1512px] mx-auto"
        style={{ height: 'calc(100vh - 72px)' }}
      >
        <div className="flex-1 max-w-[600px]" style={fadeUp(heroIn, 0)}>
          <h1 className="font-['Lato'] font-semibold text-[56px] leading-[1.1] text-black">
            A <em style={{ fontStyle: 'italic' }}>Smarter</em> Marketplace<br />for Invoice Financing
          </h1>
          <p className="mt-6 font-['Lato'] text-xl text-[#16322e] leading-relaxed">
            InvoiceFlow is a digital invoice-financing platform where businesses sell unpaid invoices to investors
            in exchange for immediate cash, while investors earn short-term returns.
          </p>
          <Link
            to="/register"
            className="inline-block mt-8 bg-teal text-white font-['Lato'] font-semibold text-base px-7 py-3 rounded-[22px] hover:opacity-90 transition-opacity"
          >
            Get Started
          </Link>
        </div>
        <div className="flex-shrink-0 flex items-center justify-center" style={fadeUp(heroIn, 120)}>
          <img
            src={imgIphone}
            alt="InvoiceFlow mobile app"
            style={{ maxHeight: 'calc(100vh - 120px)', width: 'auto', maxWidth: '360px' }}
            className="object-contain"
          />
        </div>
      </section>

      {/* ── BENTO GRID ── */}
      <section
        ref={bentoRef}
        className="px-8 lg:px-16 py-10 max-w-[1512px] mx-auto"
        style={{ height: '100vh' }}
      >
        <div className="flex flex-col gap-4 h-full">

          {/* Row 1 — 4fr : 3fr : 4fr */}
          <div
            className="grid gap-4 flex-1 min-h-0"
            style={{ gridTemplateColumns: '4fr 3fr 4fr' }}
          >
            {/* Photo card — businesses */}
            <div className="h-full" style={fadeUp(bentoIn, 0)}>
              <div className="bento-card relative rounded-[15px] overflow-hidden h-full">
                <img src={imgBusiness} alt="For businesses" className="absolute inset-0 w-full h-full object-cover" />
                <div className="absolute inset-0" style={{ background: 'linear-gradient(180deg,rgba(0,0,0,0) 0%,rgba(0,0,0,0) 55%,rgba(0,0,0,.5) 80%,rgba(0,0,0,.82) 100%)' }} />
                <div className="absolute top-4 left-5 bg-black/40 backdrop-blur-sm rounded-lg px-3 py-1">
                  <span className="font-['Lato'] font-medium text-[#fffcf7] text-sm">For businesses</span>
                </div>
                <p className="absolute bottom-7 left-5 font-['Lato'] font-semibold text-[#fffcf7] text-[28px] leading-tight max-w-[280px]">
                  Get paid in days, not months
                </p>
              </div>
            </div>

            {/* Stat card */}
            <div className="h-full" style={fadeUp(bentoIn, 80)}>
              <div className="bento-card bg-cream rounded-[15px] h-full flex flex-col justify-between p-7 overflow-hidden">
                <p className="font-['Lato'] font-semibold text-[56px] text-black leading-none">$4.2M+</p>
                <p className="font-['Lato'] text-lg text-black leading-snug">In invoices listed to date</p>
              </div>
            </div>

            {/* Stripe card */}
            <div className="h-full" style={fadeUp(bentoIn, 160)}>
              <div className="bento-card bg-teal rounded-[15px] h-full p-7 flex flex-col">
                <img src={imgStripe} alt="Stripe" className="h-9 w-auto object-contain self-start" />
                <div className="mt-auto">
                  <p className="font-['Lato'] font-semibold text-[#fffcf7] text-[26px] leading-tight">
                    Secure payments via Stripe
                  </p>
                  <p className="mt-2 font-['Lato'] text-[#fffcf7]/80 text-sm leading-snug">
                    Wallet top-up and payments handled quickly and safely through Stripe
                  </p>
                </div>
              </div>
            </div>
          </div>

          {/* Row 2 — 9fr : 11fr : 14fr */}
          <div
            className="grid gap-4 flex-1 min-h-0"
            style={{ gridTemplateColumns: '9fr 11fr 14fr' }}
          >
            {/* Stats card */}
            <div className="h-full" style={fadeUp(bentoIn, 240)}>
              <div className="bento-card bg-teal rounded-[15px] h-full p-7 flex flex-col justify-between">
                <div>
                  <span className="font-['Lato'] font-semibold text-[#fffbf4] text-[60px] leading-none">2.3</span>
                  <span className="font-['Lato'] text-[#fffbf4] text-2xl ml-2">days</span>
                  <p className="font-['Lato'] text-[#fffbf4]/70 text-base mt-1">average funding time</p>
                </div>
                <div>
                  <p className="font-['Lato'] font-semibold text-[#fffbf4] text-4xl">95%</p>
                  <p className="font-['Lato'] text-[#fffbf4]/70 text-base mt-1">successful auctions</p>
                </div>
              </div>
            </div>

            {/* Photo card — investors */}
            <div className="h-full" style={fadeUp(bentoIn, 320)}>
              <div className="bento-card relative rounded-[15px] overflow-hidden h-full">
                <img src={imgInvestor} alt="For investors" className="absolute inset-0 w-full h-full object-cover" />
                <div className="absolute inset-0" style={{ background: 'linear-gradient(180deg,rgba(0,0,0,0) 0%,rgba(0,0,0,0) 45%,rgba(0,0,0,.5) 75%,rgba(0,0,0,.85) 100%)' }} />
                <div className="absolute top-4 left-5 bg-black/40 backdrop-blur-sm rounded-lg px-3 py-1">
                  <span className="font-['Lato'] font-medium text-[#fffcf7] text-sm">For investors</span>
                </div>
                <p className="absolute bottom-10 left-5 font-['Lato'] font-semibold text-[#fffcf7] text-[22px] leading-tight max-w-[320px]">
                  Short-term returns, backed by real invoices
                </p>
                <p className="absolute bottom-4 left-5 font-['Lato'] text-[#fffcf7]/80 text-xs max-w-[320px]">
                  Browse verified listings and bid with full transparency before committing funds.
                </p>
              </div>
            </div>

            {/* ACRA card */}
            <div className="h-full" style={fadeUp(bentoIn, 400)}>
              <div className="bento-card bg-slate rounded-[15px] h-full p-7 flex flex-col">
                <p className="font-['Lato'] font-semibold text-[#fffcf7] text-[24px] leading-tight">
                  Verified invoice listings
                </p>
                <p className="mt-3 font-['Lato'] text-[#fffcf7]/70 text-sm leading-snug">
                  Every debtor is checked against the ACRA UEN registry
                </p>
                <div className="mt-auto flex justify-end">
                  <img src={imgAcra} alt="ACRA" className="h-12 w-auto object-contain" />
                </div>
              </div>
            </div>
          </div>

        </div>
      </section>

      {/* ── VALUE PROPS ── */}
      <section ref={valueRef} className="px-8 lg:px-16 pt-20 pb-36 mt-24 max-w-[1512px] mx-auto grid grid-cols-2 gap-16">
        <div style={fadeUp(valueIn, 0)}>
          <p className="font-['Lato'] text-xl text-black mb-3">For Businesses</p>
          <h2 className="font-['Lato'] font-semibold text-[34px] leading-tight text-black">
            Stop waiting 90 days to get paid.
          </h2>
          <p className="mt-5 font-['Lato'] text-lg text-black leading-relaxed">
            Your invoice, your terms. You control the auction. Set a minimum bid to protect your margin and choose how long it runs. Capital lands in your account the same day it closes.
          </p>
          <Link to="/register" className="inline-flex items-center gap-3 mt-7 font-['Lato'] text-lg text-black hover:opacity-70 transition-opacity">
            <img src={iconArrow} alt="" className="w-6 h-6" />
            Get Started
          </Link>
        </div>
        <div style={fadeUp(valueIn, 80)}>
          <p className="font-['Lato'] text-xl text-black mb-3">For Investors</p>
          <h2 className="font-['Lato'] font-semibold text-[34px] leading-tight text-black">
            Short-duration assets.<br />Verified debtors.
          </h2>
          <p className="mt-5 font-['Lato'] text-lg text-black leading-relaxed">
            Filter listings by urgency level to find motivated sellers offering better discounts. Every listing shows minimum bid upfront.
          </p>
          <Link to="/register" className="inline-flex items-center gap-3 mt-7 font-['Lato'] text-lg text-black hover:opacity-70 transition-opacity">
            <img src={iconArrow} alt="" className="w-6 h-6" />
            Start Investing
          </Link>
        </div>
      </section>

      {/* ── HOW IT WORKS ── */}
      <section ref={howRef} className="bg-cream py-20 mt-24">
        <div className="px-8 lg:px-16 max-w-[1512px] mx-auto">
          <div className="flex flex-col lg:flex-row lg:items-start gap-16 mb-10" style={fadeUp(howIn, 0)}>
            <h2 className="font-['Lato'] font-semibold text-[64px] text-black leading-none flex-shrink-0">
              How it Works
            </h2>
            <p className="font-['Lato'] text-2xl text-black leading-relaxed max-w-[643px]">
              Whether you're unlocking cash from unpaid invoices or looking for short-term returns, InvoiceFlow keeps the process simple from start to finish.
            </p>
          </div>
          <div className="flex gap-3 mb-12" style={fadeUp(howIn, 80)}>
            {['business', 'investor'].map(tab => (
              <button
                key={tab}
                onClick={() => setHowTab(tab)}
                className={`font-['Lato'] font-semibold text-base px-7 py-2.5 rounded-[22px] transition-colors duration-150 ${
                  howTab === tab
                    ? 'bg-teal text-white'
                    : 'border border-teal text-teal bg-transparent hover:bg-teal/5'
                }`}
              >
                {tab === 'business' ? 'For Businesses' : 'For Investors'}
              </button>
            ))}
          </div>
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-8">
            {howSteps.map((step, i) => (
              <div key={step.num} style={fadeUp(howIn, 160 + i * 80)}>
                <p className="font-['Lato'] text-2xl text-black mb-2">{step.num}</p>
                <p className="font-['Lato'] font-medium text-[26px] text-black mb-3 leading-tight">{step.title}</p>
                <p className="font-['Lato'] font-light text-xl text-black leading-relaxed">{step.body}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── FAQ ── */}
      <section ref={faqRef} className="bg-teal py-20">
        <div className="px-8 lg:px-16 max-w-[1512px] mx-auto" style={fadeUp(faqIn, 0)}>
          <p className="font-['Lato'] font-medium text-[#fff8ec] text-2xl mb-2">FAQ</p>
          <h2 className="font-['Lato'] font-semibold text-[#fff8ec] text-5xl mb-2">Common questions</h2>
          <p className="font-['Lato'] text-[#fff8ec] text-2xl mb-8">
            Everything you need to know before you list or bid.
          </p>
          <div className="flex gap-3 mb-10">
            {['business', 'investor'].map(tab => (
              <button
                key={tab}
                onClick={() => setFaqTab(tab)}
                className={`font-['Lato'] font-semibold text-base px-7 py-2.5 rounded-[22px] transition-colors duration-150 ${
                  faqTab === tab
                    ? 'bg-[#fff8ec] text-teal'
                    : 'border border-[#fff8ec] text-[#fff8ec] hover:bg-white/10'
                }`}
              >
                {tab === 'business' ? 'For Businesses' : 'For Investors'}
              </button>
            ))}
          </div>
          <div className="bg-[#fff8ec] rounded-[15px] overflow-hidden max-w-[1319px]">
            {faqItems.map((item, i) => (
              <div key={item.question} style={fadeUp(faqIn, 160 + i * 80)}>
                <FAQItem question={item.question} answer={item.answer} />
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── TEAM ── */}
      <section ref={teamRef} className="py-24 px-8 lg:px-16 max-w-[1512px] mx-auto">
        <h2
          className="font-['Lato'] font-semibold text-4xl text-black text-center mb-16"
          style={fadeUp(teamIn, 0)}
        >
          Our Team
        </h2>
        <div className="grid grid-cols-3 gap-12 max-w-[900px] mx-auto">
          {TEAM.map((name, i) => (
            <div key={name} className="flex flex-col items-center gap-4" style={fadeUp(teamIn, i * 80)}>
              <div className="w-[180px] h-[180px] rounded-full bg-cream border border-black/10" />
              <p className="font-['Lato'] font-semibold text-xl text-black text-center">{name}</p>
            </div>
          ))}
        </div>
      </section>

      {/* ── FOOTER ── */}
      <footer className="bg-teal px-8 lg:px-16 py-8">
        <div className="max-w-[1512px] mx-auto flex items-center justify-between">
          <p className="font-['Lato'] font-bold text-xl text-[#fff8ec]">InvoiceFlow</p>
          <p className="font-['Lato'] text-sm text-[#fff8ec]/60">
            © {new Date().getFullYear()} InvoiceFlow · SMU IS213
          </p>
        </div>
      </footer>
    </div>
  )
}
