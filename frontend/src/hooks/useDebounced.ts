import { useEffect, useState } from 'react'

/** Wert erst nach kurzer Tipp-Pause übernehmen (verhindert eine Serverabfrage pro Tastendruck). */
export function useDebounced<T>(value: T, delayMs = 300): T {
  const [debounced, setDebounced] = useState(value)
  useEffect(() => {
    const t = setTimeout(() => setDebounced(value), delayMs)
    return () => clearTimeout(t)
  }, [value, delayMs])
  return debounced
}
