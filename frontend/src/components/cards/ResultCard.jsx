import { api } from '../../api/client.js'
import { fmtBytes, fmtClock } from '../../lib/format.js'
import Icon from '../icons/Icon.jsx'
import { Badge } from '../ui/Badge.jsx'
import { CardShell, Empty, Scrim } from './CardShell.jsx'

// a finished (or failed) file inside a job
export function ResultCard({ jobId, item, onOpen }) {
	const isDone = item.status === 'done'
	return (
		<CardShell onClick={isDone ? onOpen : undefined} label={isDone ? `View ${item.out_name}` : undefined}>
			{isDone && item.thumb ? <img src={api.thumbUrl(jobId, item.id)} alt="" loading="lazy" className="absolute inset-0 size-full object-cover" /> : <Empty kind={item.kind} />}
			<Scrim />
			<div className="absolute left-3 top-3 flex gap-1.5">
				<Badge tone="glass">
					<Icon name={item.kind} className="size-3.5" />
					{item.kind === 'image' ? 'Image' : 'Video'}
				</Badge>
				{!isDone && <Badge tone="bad">{item.status === 'cancelled' ? 'Cancelled' : 'Failed'}</Badge>}
			</div>
			{isDone && (
				<a 
					href={api.fileUrl(jobId, item.id)} 
					onClick={(event) => event.stopPropagation()} 
					aria-label={`Download ${item.out_name}`}
					className="absolute right-2.5 top-2.5 grid size-9 place-items-center rounded-full bg-black/55 text-white backdrop-blur transition hover:bg-accent hover:text-accent-ink sm:opacity-0 sm:group-hover:opacity-100 sm:focus-visible:opacity-100"
				>
					<Icon name="download" className="size-4.5" />
				</a>
			)}
			{item.kind === 'video' && isDone && (
				<span className="pointer-events-none absolute inset-0 grid place-items-center">
					<span className="grid size-12 place-items-center rounded-full bg-black/50 text-white backdrop-blur">
						<Icon name="play" className="ml-0.5 size-5" />
					</span>
				</span>
			)}
			<div className="absolute inset-x-0 bottom-0 p-3.5 text-white">
				<p className="truncate text-sm font-semibold" title={item.out_name || item.name}>{item.out_name || item.name}</p>
				{isDone
					? <p className="tnum truncate text-xs text-white/75">{item.w && `${item.w}×${item.h} · `}{fmtBytes(item.size)}{item.kind === 'video' && item.duration ? ` · ${fmtClock(item.duration)}` : ''}</p>
					: <p className="line-clamp-2 text-xs text-red-200" title={item.error}>{item.error || item.message}</p>}
			</div>
		</CardShell>
	)
}
