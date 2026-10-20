export function Field({ label, hint, children, className = '' }) {
	return (
		<div className={`space-y-2.5 ${className}`}>
			{(label || hint) && (
				<div className="flex items-baseline justify-between gap-3">
					{label && <span className="text-sm font-semibold">{label}</span>}
					{hint && <span className="text-right text-xs text-muted">{hint}</span>}
				</div>
			)}
			{children}
		</div>
	)
}

export const inputCls = 'h-11 w-full min-w-0 rounded-xl bg-surface px-3.5 text-[15px] ring-1 ring-line placeholder:text-muted/70 focus:ring-2 focus:ring-accent focus:outline-none'
