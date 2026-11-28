import { fmtDate } from '../../lib/format.js'
import Icon from '../icons/Icon.jsx'
import { btn } from '../ui/buttonStyles.js'
import { CardShell } from './CardShell.jsx'

// a job that is listed in job-locations.json but whose folder can't be reached right now. not clickable.
export function LostJobCard({ job, onRetry, onRemove }) {
	return (
		<CardShell className="cursor-default !bg-surface ring-dashed">
			<div className="absolute inset-0 flex flex-col gap-2 p-4">
				<span className="grid size-10 place-items-center rounded-xl bg-warn/15 text-warn"><Icon name="alert" className="size-5" /></span>
				<p className="text-sm font-semibold">Can&apos;t reach this job</p>
				<p className="text-xs text-muted">{job.reason}. Reconnect the drive, or fix the path in <code>job-locations.json</code>, then check again.</p>
				<code className="min-h-0 flex-1 overflow-auto break-all font-mono text-[11px] leading-4 text-muted" title={job.path}>{job.path}</code>
				<p className="tnum text-xs text-muted">{job.created ? fmtDate(job.created) : ''}</p>
				<div className="flex gap-2">
					<button type="button" onClick={onRetry} className={btn('secondary', 'sm', 'flex-1')}>Check again</button>
					<button type="button" onClick={onRemove} className={btn('ghost', 'sm')} aria-label="Remove from the list" title="Remove from the list (no files are touched)"><Icon name="trash" className="size-4" /></button>
				</div>
			</div>
		</CardShell>
	)
}
