// ---- a thin progress bar ----------------------------------------------------
// value is 0 to 1. indeterminate shows a sliding stripe when the progress isn't known yet.
export function ProgressBar({ value = 0, indeterminate = false, tone = 'accent', className = 'h-2' }) {
	const colour = tone === 'ok' ? 'bg-ok' : tone === 'bad' ? 'bg-bad' : 'bg-accent'
	return (
		<div className={`overflow-hidden rounded-full bg-sunken ${className}`} role="progressbar" aria-valuemin={0} aria-valuemax={100} aria-valuenow={indeterminate ? undefined : Math.round(value * 100)}>
			{indeterminate
				? <div className={`anim-slide h-full w-2/5 rounded-full ${colour}`} />
				: <div className={`h-full rounded-full ${colour} transition-[width] duration-300`} style={{ width: `${Math.round(Math.min(1, Math.max(0, value)) * 100)}%` }} />}
		</div>
	)
}
