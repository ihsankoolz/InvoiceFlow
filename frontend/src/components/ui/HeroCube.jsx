import { useEffect, useRef } from 'react'

const SIZE = 140 // px — half-size of the cube face offset

const FACES = [
  { label: 'INVOICES',  value: '$2.4M',  transform: `translateZ(${SIZE}px)` },
  { label: 'FUNDED',    value: '98%',    transform: `rotateY(180deg) translateZ(${SIZE}px)` },
  { label: 'BUYERS',    value: '1,200+', transform: `rotateY(90deg) translateZ(${SIZE}px)` },
  { label: 'SELLERS',   value: '340+',   transform: `rotateY(-90deg) translateZ(${SIZE}px)` },
  { label: 'AVG YIELD', value: '8.2%',   transform: `rotateX(90deg) translateZ(${SIZE}px)` },
  { label: 'SETTLED',   value: '24 hrs', transform: `rotateX(-90deg) translateZ(${SIZE}px)` },
]

export default function HeroCube() {
  const cubeRef = useRef(null)
  const frameRef = useRef(null)
  const rotRef = useRef({ x: 18, y: 0 })

  useEffect(() => {
    let last = performance.now()

    function tick(now) {
      const dt = (now - last) / 1000
      last = now
      rotRef.current.y += 28 * dt   // degrees per second
      rotRef.current.x = 18 + Math.sin(rotRef.current.y * (Math.PI / 180) * 0.4) * 10
      if (cubeRef.current) {
        cubeRef.current.style.transform =
          `rotateX(${rotRef.current.x}deg) rotateY(${rotRef.current.y}deg)`
      }
      frameRef.current = requestAnimationFrame(tick)
    }

    frameRef.current = requestAnimationFrame(tick)
    return () => cancelAnimationFrame(frameRef.current)
  }, [])

  return (
    <div
      style={{
        width:  SIZE * 2,
        height: SIZE * 2,
        perspective: 900,
        perspectiveOrigin: '50% 50%',
      }}
      aria-hidden="true"
    >
      {/* scene */}
      <div style={{ width: '100%', height: '100%', position: 'relative', transformStyle: 'preserve-3d' }}>
        {/* cube wrapper — rotated by rAF */}
        <div
          ref={cubeRef}
          style={{
            width:  SIZE * 2,
            height: SIZE * 2,
            position: 'absolute',
            inset: 0,
            transformStyle: 'preserve-3d',
          }}
        >
          {FACES.map(({ label, value, transform }) => (
            <div
              key={label}
              style={{
                position: 'absolute',
                inset: 0,
                transform,
                transformStyle: 'preserve-3d',
                backfaceVisibility: 'hidden',
                /* glass face */
                background: 'rgba(255,252,247,0.06)',
                border: '1px solid rgba(255,149,0,0.35)',
                borderRadius: 12,
                display: 'flex',
                flexDirection: 'column',
                alignItems: 'center',
                justifyContent: 'center',
                gap: 6,
                backdropFilter: 'blur(4px)',
                boxShadow: 'inset 0 0 24px rgba(255,149,0,0.08), 0 0 18px rgba(255,149,0,0.12)',
              }}
            >
              <span style={{
                fontFamily: 'Lato, sans-serif',
                fontSize: 10,
                fontWeight: 700,
                letterSpacing: '0.15em',
                color: 'rgba(255,149,0,0.85)',
                textTransform: 'uppercase',
              }}>
                {label}
              </span>
              <span style={{
                fontFamily: '"Playfair Display", serif',
                fontSize: 26,
                fontWeight: 600,
                color: '#222222',
                lineHeight: 1,
              }}>
                {value}
              </span>
            </div>
          ))}
        </div>

        {/* subtle drop shadow plane */}
        <div style={{
          position: 'absolute',
          bottom: -24,
          left: '50%',
          transform: 'translateX(-50%)',
          width: SIZE * 1.6,
          height: 24,
          borderRadius: '50%',
          background: 'radial-gradient(ellipse, rgba(34,34,34,0.18) 0%, transparent 70%)',
          filter: 'blur(4px)',
        }} />
      </div>
    </div>
  )
}
