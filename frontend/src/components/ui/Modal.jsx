import { useEffect, useRef } from 'react'

// ---- modal ----------------------------------------------------------------
export function Modal({ open, onClose, children, label, size = 'md', closable = true }) {
	const ref = useRef(null)

	useEffect(() => {
		if (!open) return
		const prev = document.activeElement
		ref.current?.focus()
		const key = (event) => { if (event.key === 'Escape' && closable) onClose?.() }
		document.addEventListener('keydown', key)
		document.body.style.overflow = 'hidden'
		return () => { document.removeEventListener('keydown', key); document.body.style.overflow = ''; prev?.focus?.() }
	}, [open, onClose, closable])

	if (!open) return null
	const width = { md: 'max-w-lg', lg: 'max-w-3xl', xl: 'max-w-6xl' }[size]

	return (
		<div className="fixed inset-0 z-50 grid place-items-center overflow-y-auto p-4 sm:p-8">
			<div className="anim-fade fixed inset-0 bg-black/60 backdrop-blur-sm" onClick={closable ? onClose : undefined} />
			<div 
				ref={ref} 
				tabIndex={-1} 
				role="dialog" 
				aria-modal="true" 
				aria-label={label}
				className={`anim-pop relative w-full ${width} rounded-3xl bg-surface p-6 ring-1 ring-line shadow-2xl outline-none sm:p-8`}
			>
				{children}
			</div>
		</div>
	)
}
