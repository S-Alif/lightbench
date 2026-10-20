import { createContext, useCallback, useContext, useState } from 'react'
import Icon from '../icons/Icon.jsx'

// toasts
const ToastCtx = createContext(() => { })

export const useToast = () => useContext(ToastCtx)

export function ToastProvider({ children }) {
	const [items, setItems] = useState([])
	
	const push = useCallback((text, tone = 'ok') => {
		const id = Math.random().toString(36).slice(2)
		setItems((currentItems) => [...currentItems, { id, text, tone }])
		setTimeout(() => setItems((currentItems) => currentItems.filter((toastItem) => toastItem.id !== id)), 4200)
	}, [])

	return (
		<ToastCtx.Provider value={push}>
			{children}
			<div className="pointer-events-none fixed inset-x-0 bottom-6 z-60 flex flex-col items-center gap-2 px-4" aria-live="polite">
				{items.map((toastItem) => (
					<div key={toastItem.id} className="anim-pop pointer-events-auto flex items-center gap-2.5 rounded-xl bg-ink px-4 py-3 text-sm font-medium text-bg shadow-2xl">
						<Icon name={toastItem.tone === 'bad' ? 'alert' : 'check'} className={`size-4 ${toastItem.tone === 'bad' ? 'text-bad' : 'text-ok'}`} />
						{toastItem.text}
					</div>
				))}
			</div>
		</ToastCtx.Provider>
	)
}
