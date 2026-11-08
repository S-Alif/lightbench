import { useEffect, useRef } from 'react'

// ---- modal ----------------------------------------------------------------
// padded={false} lets the content (like the editor) lay out the whole panel itself
export function Modal({ open, onClose, children, label, size = 'md', closable = true, padded = true }) {
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
	const width = { md: 'max-w-lg', lg: 'max-w-3xl', xl: 'max-w-6xl', '2xl': 'max-w-7xl' }[size]

	return (
		<div className="fixed inset-0 z-50 flex min-h-full overflow-y-auto p-4 sm:p-8">
			<div className="anim-fade fixed inset-0 bg-black/60 backdrop-blur-sm" onClick={closable ? onClose : undefined} />
			{/* m-auto centres the panel, and unlike place-items-center it never pushes the top out of reach when the panel is taller than the screen */}
			<div 
				ref={ref} 
				tabIndex={-1} 
				role="dialog" 
				aria-modal="true" 
				aria-label={label}
				className={`anim-pop relative m-auto w-full ${width} rounded-3xl bg-surface ring-1 ring-line shadow-2xl outline-none focus-visible:outline-none ${padded ? 'p-6 sm:p-8' : 'overflow-clip'}`}
			>
				{children}
			</div>
		</div>
	)
}
