import { useEffect, useState } from 'react'
import { fmtClock, plural } from '../../lib/format.js'
import { summarizeRun } from '../../lib/runStats.js'
import { btn } from '../ui/buttonStyles.js'
import { ProgressBar } from '../ui/ProgressBar.jsx'
import Icon from '../icons/Icon.jsx'
import ResourceMonitor from './ResourceMonitor.jsx'

const Stat = ({ value, label, tone = '' }) => (
	<div>
		<p className={`tnum text-lg font-semibold ${tone}`}>{value}</p>
		<p className="text-xs text-muted">{label}</p>
	</div>
)

/**
 * shown above the file cards while a job uploads, runs and when it has finished.
 * run = { phase: 'uploading' | 'processing' | 'done' | 'error', upload: 0..1, job, error }
 */
export default function RunPanel({ run, onCancel, onView, onNewBatch, onDismiss }) {
	const [startedAt] = useState(Date.now())
	const [now, setNow] = useState(Date.now())
	useEffect(() => {
		const intervalId = setInterval(() => setNow(Date.now()), 500)
		return () => clearInterval(intervalId)
	}, [])

	const { phase } = run
	const stats = summarizeRun(run, (now - startedAt) / 1000)
	const { total, finished, failed, succeeded, current, overall, elapsed, remaining } = stats
	const live = phase === 'uploading' || phase === 'processing'

	let title = 'Processing…', tone = 'accent', progress = overall
	if (phase === 'uploading') { title = 'Uploading files…'; progress = run.upload }
	else if (phase === 'error') { title = 'Something went wrong'; tone = 'bad'; progress = 0 }
	else if (phase === 'done') {
		progress = 1
		tone = succeeded === 0 ? 'bad' : 'ok'
		title = succeeded === 0 ? 'Nothing could be processed' : failed ? 'Finished with some errors' : 'All done'
	}

	return (
		<section aria-label="Job progress" className="space-y-5 rounded-3xl bg-surface p-5 ring-1 ring-line sm:p-6">
			<div className="flex flex-wrap items-center justify-between gap-3">
				<div className="flex min-w-0 items-center gap-2.5">
					{phase === 'done' && <Icon name={tone === 'ok' ? 'check' : 'alert'} className={`size-5 ${tone === 'ok' ? 'text-ok' : 'text-bad'}`} />}
					{phase === 'error' && <Icon name="alert" className="size-5 text-bad" />}
					<h2 className="truncate text-lg font-semibold" aria-live="polite">{title}</h2>
				</div>
				<div className="flex flex-wrap gap-2.5">
					{phase === 'processing' && <button type="button" className={btn('secondary', 'sm')} onClick={onCancel}>Cancel remaining</button>}
					{phase === 'done' && (
						<>
							<button type="button" className={btn('ghost', 'sm')} onClick={onNewBatch}>Start new batch</button>
							<button type="button" className={btn('primary', 'sm')} onClick={onView} autoFocus>
								{succeeded > 0 ? `View ${plural(succeeded, 'result')}` : 'See what went wrong'}
							</button>
						</>
					)}
					{phase === 'error' && <button type="button" className={btn('primary', 'sm')} onClick={onDismiss} autoFocus>Close</button>}
				</div>
			</div>

			{phase !== 'error' && (
				<div className="space-y-2">
					<div className="flex items-center gap-3">
						<ProgressBar value={progress} tone={tone} indeterminate={phase === 'processing' && overall === 0 && current?.status === 'queued'} className="h-2.5 flex-1" />
						<span className="tnum w-11 text-right text-sm font-medium">{Math.round(progress * 100)}%</span>
					</div>
					{phase === 'uploading' && <p className="text-sm text-muted">Sending your files to the local server.</p>}
					{phase === 'processing' && current && (
						<p className="truncate text-sm text-muted" aria-live="polite" title={current.name}>
							<span className="tnum">{Math.min(finished + 1, total)} / {total}</span> · {current.name}{current.message ? ` · ${current.message}` : ''}
						</p>
					)}
				</div>
			)}
			{phase === 'error' && <p className="text-sm text-bad">{run.error}</p>}

			{total > 0 && phase !== 'uploading' && phase !== 'error' && (
				<div className="grid grid-cols-3 gap-3 rounded-2xl bg-sunken p-4 text-center">
					<Stat value={fmtClock(elapsed)} label="elapsed" />
					<Stat value={phase === 'done' ? succeeded : remaining == null ? '–' : `~${fmtClock(remaining)}`} label={phase === 'done' ? 'processed' : 'remaining'} />
					<Stat value={failed ? `${failed} failed` : `${finished}/${total}`} label={failed ? 'errors' : 'files done'} tone={failed ? 'text-bad' : ''} />
				</div>
			)}

			{live && <ResourceMonitor />}
		</section>
	)
}
