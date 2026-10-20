import { useEffect, useState } from 'react'
import { fmtClock, plural } from '../../lib/format.js'
import Icon from '../icons/Icon.jsx'
import { btn } from '../ui/buttonStyles.js'

// progress ring
function Ring({ value, tone = 'accent', size = 188, children }) {
	const stroke = 12
	const radius = (size - stroke) / 2
	const circumference = 2 * Math.PI * radius
	return (
		<div className="relative mx-auto grid place-items-center" style={{ width: size, height: size }}>
			<svg width={size} height={size} viewBox={`0 0 ${size} ${size}`} className="-rotate-90" aria-hidden="true">
				<circle cx={size / 2} cy={size / 2} r={radius} fill="none" stroke="var(--sunken)" strokeWidth={stroke} />
				<circle cx={size / 2} cy={size / 2} r={radius} fill="none" strokeWidth={stroke} strokeLinecap="round"
					stroke={tone === 'ok' ? 'var(--ok)' : tone === 'bad' ? 'var(--bad)' : 'var(--accent)'}
					strokeDasharray={circumference} strokeDashoffset={circumference * (1 - Math.min(1, Math.max(0, value)))} className="ring-fill" />
			</svg>
			<div className="absolute inset-0 grid place-items-center">{children}</div>
		</div>
	)
}

function Line({ value, indeterminate }) {
	return (
		<div className="h-2 overflow-hidden rounded-full bg-sunken" role="progressbar" aria-valuemin={0} aria-valuemax={100} aria-valuenow={indeterminate ? undefined : Math.round(value * 100)}>
			{indeterminate
				? <div className="anim-slide h-full w-2/5 rounded-full bg-accent" />
				: <div className="h-full rounded-full bg-accent transition-[width] duration-300" style={{ width: `${Math.round(value * 100)}%` }} />}
		</div>
	)
}

// run = { phase: 'uploading' | 'processing' | 'done' | 'error', upload: 0..1, job, error }
export default function Overlay({ run, onCancel, onView, onClose }) {
	const [now, setNow] = useState(Date.now())
	const [startedAt] = useState(Date.now())

	useEffect(() => { 
		const intervalId = setInterval(() => setNow(Date.now()), 500)
		return () => clearInterval(intervalId) 
	}, [])

	const { phase, job } = run
	const items = job?.items || []
	const total = items.length
	const finished = items.filter((item) => ['done', 'error', 'cancelled'].includes(item.status)).length
	const failed = items.filter((item) => item.status === 'error').length
	const doneN = items.filter((item) => item.status === 'done').length
	const current = items.find((item) => item.status === 'running') || items.find((item) => item.status === 'queued')
	const overall = total ? items.reduce((sum, item) => sum + (['done', 'error', 'cancelled'].includes(item.status) ? 1 : item.progress || 0), 0) / total : 0

	const elapsed = job?.elapsed ?? (now - startedAt) / 1000
	const eta = overall > 0.03 && phase === 'processing' ? (elapsed * (1 - overall)) / overall : null

	let pct, title, tone = 'accent'
	
	if (phase === 'uploading') { 
		pct = run.upload
		title = 'Uploading files…' 
	}
	else if (phase === 'error') { 
		pct = 0 
		title = 'Something went wrong'
		tone = 'bad' 
	}
	else if (phase === 'done') {
		pct = 1
		tone = doneN === 0 ? 'bad' : 'ok'
		title = doneN === 0 ? 'Nothing could be processed' : failed ? 'Finished with some errors' : 'All done'
	} 
	else { 
		pct = overall
		title = 'Processing…'
	}

	const downloading = phase === 'processing' && current?.message?.startsWith('Downloading model')

	return (
		<div className="fixed inset-0 z-50 grid place-items-center p-4 sm:p-8">
			<div className="anim-fade absolute inset-0 bg-bg/80 backdrop-blur-md" />
			<div 
				role="dialog" aria-modal="true" 
				aria-label={title}
				className="anim-pop relative w-full max-w-md rounded-3xl bg-surface p-7 text-center ring-1 ring-line shadow-2xl sm:p-9"
			>
				<p className="mb-6 text-lg font-semibold">{title}</p>

				<Ring value={pct} tone={tone}>
					{phase === 'done' && tone === 'ok' ? (
						<Icon name="check" className="size-16 text-ok" strokeWidth={2.4} />
					) : phase === 'error' ? (
						<Icon name="alert" className="size-14 text-bad" />
					) : (
						<span className="tnum text-5xl font-semibold tracking-tight">{Math.round(pct * 100)}<span className="text-2xl text-muted">%</span></span>
					)}
				</Ring>

				{/* uploading */}
				{phase === 'uploading' && <p className="mt-6 text-sm text-muted">Sending your files to the local server.</p>}

				{/* error */}
				{phase === 'error' && <p className="mt-6 text-sm text-bad">{run.error}</p>}

				{/* processing */}
				{(phase === 'processing' || phase === 'done') && total > 0 && (
					<div className="mt-7 space-y-5 text-left">
						{phase === 'processing' && current && (
							<div className="space-y-2.5">
								<div className="flex items-baseline justify-between gap-3 text-sm">
									<span className="min-w-0 truncate font-medium" title={current.name}>
										<span className="tnum text-muted">{Math.min(finished + 1, total)} / {total} · </span>{current.name}
									</span>
									<span className="tnum shrink-0 text-muted">{Math.round((current.progress || 0) * 100)}%</span>
								</div>
								<Line 
									value={current.progress || 0} 
									indeterminate={current.status === 'queued' || (current.progress || 0) === 0 && !downloading} 
								/>
								<p className="min-h-5 text-xs text-muted" aria-live="polite">{current.message || 'Starting…'}</p>
							</div>
						)}

						<div className="grid grid-cols-3 gap-3 rounded-2xl bg-sunken p-4 text-center">
							<div>
								<p className="tnum text-lg font-semibold">
									{fmtClock(elapsed)}
								</p>
								<p className="text-xs text-muted">elapsed</p>
							</div>

							<div>
								<p className="tnum text-lg font-semibold">
									{phase === 'done' ? `${doneN}` : eta == null ? '–' : `~${fmtClock(eta)}`}
								</p>
								<p className="text-xs text-muted">{phase === 'done' ? 'processed' : 'remaining'}</p>
							</div>

							<div>
								<p className={`tnum text-lg font-semibold ${failed ? 'text-bad' : ''}`}>
									{failed ? `${failed} failed` : `${finished}/${total}`}
								</p>
								<p className="text-xs text-muted">{failed ? 'errors' : 'files done'}</p>
							</div>
						</div>
					</div>
				)}

				{/* buttons for all states */}
				<div className="mt-7 flex flex-col gap-2.5">
					{phase === 'processing' && 
						<button 
							type="button" 
							className={btn('secondary', 'md', 'w-full')} 
							onClick={onCancel}
						>
							Cancel remaining
						</button>
					}

					{(phase === 'done' && doneN > 0) && 
						<button 
							type="button" 
							autoFocus 
							className={btn('primary', 'lg', 'w-full')} 
							onClick={onView}
						>
							View {plural(doneN, 'result')}
						</button>
					}

					{(phase === 'done' && doneN === 0) && 
						<button 
							type="button" 
							autoFocus 
							className={btn('primary', 'lg', 'w-full')} 
							onClick={onView}
						>
							See what went wrong
						</button>
					}

					{phase === 'error' && 
						<button 
							type="button" 
							autoFocus 
							className={btn('primary', 'lg', 'w-full')} 
							onClick={onClose}
						>
							Close
						</button>
					}
				</div>
			</div>
		</div>
	)
}
