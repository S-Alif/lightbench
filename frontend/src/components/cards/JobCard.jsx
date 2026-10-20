import { api } from '../../api/client.js'
import { fmtBytes, fmtDate, plural } from '../../lib/format.js'
import Icon from '../icons/Icon.jsx'
import { Badge } from '../ui/Badge.jsx'
import { CardShell, Empty, Scrim } from './CardShell.jsx'

// a job in the history grid
const kindWord = (job) => (job.kind === 'mixed' ? 'file' : job.kind)

export const jobTitle = (job) => `${plural(job.count, kindWord(job))} · ${job.options?.scale > 1 ? `${job.options.scale}×` : job.options?.watermark ? 'watermark' : 'convert'}`

export function JobCard({ job, onOpen, onDelete }) {
	const thumbs = job.thumbs || []
	const active = job.status === 'running' || job.status === 'queued'
	return (
		<CardShell onClick={onOpen} label={`Open job from ${fmtDate(job.created)}`}>
			{thumbs.length === 0 ? <Empty kind={job.kind} /> : (
				<div className={`absolute inset-0 grid gap-0.5 ${thumbs.length === 1 ? '' : 'grid-cols-2'} ${thumbs.length > 2 ? 'grid-rows-2' : ''}`}>
					{thumbs.map((id) => <img key={id} src={api.thumbUrl(job.id, id)} alt="" loading="lazy" className="size-full object-cover" />)}
				</div>
			)}
			<Scrim />
			<div className="absolute left-3 top-3 flex flex-wrap gap-1.5">
				<Badge tone="glass">
					<Icon name={job.kind === 'video' ? 'video' : 'image'} className="size-3.5" />
					{job.kind === 'video' ? 'Video' : job.kind === 'mixed' ? 'Mixed' : 'Image'}
				</Badge>
				{job.status !== 'done' && <Badge tone={active ? 'accent' : job.status === 'partial' ? 'warn' : 'bad'}>{active ? 'Processing' : job.status === 'partial' ? 'Partly done' : job.status === 'cancelled' ? 'Cancelled' : 'Failed'}</Badge>}
			</div>
			<span 
				role="button" 
				tabIndex={active ? -1 : 0} 
				aria-label="Delete this job" 
				aria-disabled={active}
				onClick={(event) => { event.stopPropagation(); if (!active) onDelete() }}
				onKeyDown={(event) => { if ((event.key === 'Enter' || event.key === ' ') && !active) { event.preventDefault(); event.stopPropagation(); onDelete() } }}
				className={`absolute right-2.5 top-2.5 grid size-9 place-items-center rounded-full bg-black/55 text-white backdrop-blur transition hover:bg-bad 
					${active ? 'hidden' : 'sm:opacity-0 sm:group-hover:opacity-100 sm:focus-visible:opacity-100'}`}
			>
				<Icon name="trash" className="size-4.5" />
			</span>
			<div className="absolute inset-x-0 bottom-0 p-3.5 text-white">
				<p className="truncate text-sm font-semibold">{jobTitle(job)}</p>
				<p className="tnum truncate text-xs text-white/75">{fmtDate(job.created)}</p>
				<p className="tnum truncate text-xs text-white/60">{job.done}/{job.count} files · {fmtBytes(job.total_bytes)}</p>
			</div>
		</CardShell>
	)
}
