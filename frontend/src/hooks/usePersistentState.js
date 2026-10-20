import { useEffect, useState } from 'react'

export function useStored(key, initial) {
	const [value, setValue] = useState(() => {
		try { const storedValue = JSON.parse(localStorage.getItem(key) || 'null'); if (storedValue != null) return typeof initial === 'object' && !Array.isArray(initial) ? { ...initial, ...storedValue } : storedValue } catch { /* no storage */ }
		return initial
	})
	useEffect(() => { try { localStorage.setItem(key, JSON.stringify(value)) } catch { /* ignore */ } }, [key, value])
	return [value, setValue]
}
