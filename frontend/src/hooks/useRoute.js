import { useEffect, useState } from 'react'

// small hooks to maintain routing and navigation
export function useHashRoute() {
	const read = () => {
		if (location.hash.startsWith('#/')) {
			const clean = '/' + location.hash.replace(/^#\/?/, '')
			history.replaceState(null, '', clean)
		}
		const raw = location.hash.replace(/^#\/?/, '') || location.pathname.replace(/^\/+/, '')
		const parts = raw.split('/').filter(Boolean)
		return { page: parts[0] || 'new', id: parts[1] || null }
	}
	const [route, setRoute] = useState(read)

	useEffect(() => {
		const handleRouteChange = () => setRoute(read())
		window.addEventListener('popstate', handleRouteChange)
		window.addEventListener('hashchange', handleRouteChange)
		
		return () => {
			window.removeEventListener('popstate', handleRouteChange)
			window.removeEventListener('hashchange', handleRouteChange)
		}
	}, [])

	return route
}

export const navigateTo = (path) => {
	const clean = '/' + String(path || '').replace(/^#?\/+/, '')
	if (location.pathname !== clean || location.hash) {
		history.pushState(null, '', clean)
	}
	window.dispatchEvent(new PopStateEvent('popstate'))
}
