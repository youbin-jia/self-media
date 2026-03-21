import { useEffect, useMemo, useState } from 'react'

function easeOutCubic(t) {
  return 1 - (1 - t) ** 3
}

function AnimatedNumber({ value = 0, duration = 800, suffix = '', prefix = '' }) {
  const target = Number(value) || 0
  const [display, setDisplay] = useState(0)

  useEffect(() => {
    const start = performance.now()
    const from = display
    const delta = target - from
    let rafId

    const tick = (now) => {
      const elapsed = now - start
      const progress = Math.min(elapsed / duration, 1)
      const eased = easeOutCubic(progress)
      setDisplay(from + delta * eased)
      if (progress < 1) {
        rafId = requestAnimationFrame(tick)
      }
    }

    rafId = requestAnimationFrame(tick)
    return () => cancelAnimationFrame(rafId)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [target, duration])

  const text = useMemo(() => {
    const rounded = Math.round(display)
    return `${prefix}${rounded}${suffix}`
  }, [display, prefix, suffix])

  return text
}

export default AnimatedNumber

