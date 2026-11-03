import { useState } from 'react'
import { fmtBytes, fmtClock } from '../../lib/format.js'
import Icon from '../icons/Icon.jsx'
import { Badge } from '../ui/Badge.jsx'
import { ProgressBar } from '../ui/ProgressBar.jsx'
import { CardShell, Scrim } from './CardShell.jsx'

const STATE_LABEL = { uploading: 'Uploading', queued: 'Waiting', running: 'Processing', done: 'Done', error: 'Failed', cancelled: 'Cancelled' }
// solid colours so the badge stays readable on top of a photo
const STATE_STYLE = {
	uploading: 'bg-accent text-accent-ink', running: 'bg-accent text-accent-ink', queued: 'bg-black/55 text-white backdrop-blur',
	done: 'bg-ok text-white', error: 'bg-bad text-white', cancelled: 'bg-bad text-white',
}

// ---- a file the user picked, before upload --------------------------------
// state is set while a job runs: { kind, progress, message, error } (see lib/runStats.js)
export function PickedCard({ pickedFile, edited, onEdit, onRemove, state = null }) {
	const [meta, setMeta] = useState('')
	return (
		<CardShell>
			{pickedFile.kind === 'image'
				? <img src={pickedFile.url} alt="" className="absolute inset-0 size-full object-cover" onLoad={(event) => setMeta(`${event.target.naturalWidth}×${event.target.naturalHeight}`)} />
				: <video src={`${pickedFile.url}#t=0.1`} muted preload="metadata" className="absolute inset-0 size-full object-cover"
					onLoadedMetadata={(event) => setMeta(`${event.target.videoWidth}×${event.target.videoHeight} · ${fmtClock(event.target.duration)}`)} />}
			<Scrim />
			<div className="absolute left-3 top-3">
				<Badge tone="glass"><Icon name={pickedFile.kind} className="size-3.5" />{pickedFile.kind === 'image' ? 'Image' : 'Video'}</Badge>
				{edited && <Badge tone="accent" className="ml-1.5">Edited</Badge>}
				{state && <span className={`ml-1.5 inline-flex items-center rounded-full px-2.5 py-1 text-xs font-medium ${STATE_STYLE[state.kind]}`}>{STATE_LABEL[state.kind]}{state.kind === 'running' && state.progress > 0 ? ` ${Math.round(state.progress * 100)}%` : ''}</span>}
			</div>
			{!state && onEdit && pickedFile.kind === 'image' && (
				<button
					type="button"
					onClick={onEdit}
					aria-label={`Edit ${pickedFile.file.name}`}
					className="absolute bottom-3 right-3 z-10 inline-flex h-8 items-center gap-1.5 rounded-full bg-black/60 px-3 text-xs font-medium text-white backdrop-blur transition hover:bg-accent"
				>
					<Icon name="crop" className="size-3.5" />Edit
				</button>
			)}
			{!state && <button 
				type="button" 
				onClick={onRemove} 
				aria-label={`Remove ${pickedFile.file.name}`}
				className="absolute right-2.5 top-2.5 grid size-8 place-items-center rounded-full bg-black/55 text-white backdrop-blur transition hover:bg-bad sm:opacity-0 sm:group-hover:opacity-100 sm:focus-visible:opacity-100"
			>
				<Icon name="x" className="size-4" />
			</button>}
			<div className="absolute inset-x-0 bottom-0 p-3.5 text-white">
				<p className="truncate text-sm font-semibold" title={pickedFile.file.name}>{pickedFile.file.name}</p>
				{state && ['running', 'uploading'].includes(state.kind) && (
					<div className="mb-2">
						<ProgressBar value={state.progress || 0} indeterminate={state.kind === 'uploading' ? false : (state.progress || 0) === 0} className="h-1.5" />
					</div>
				)}
				<p className="tnum truncate text-xs text-white/75" title={state?.error || undefined}>
					{state?.kind === 'error' ? state.error : `${fmtBytes(pickedFile.file.size)}${meta ? ` · ${meta}` : ''}`}
				</p>
			</div>
		</CardShell>
	)
}
