import { useState } from 'react'
import { fmtBytes, fmtClock } from '../../lib/format.js'
import Icon from '../icons/Icon.jsx'
import { Badge } from '../ui/Badge.jsx'
import { CardShell, Scrim } from './CardShell.jsx'

// a file the user picked, before upload
export function PickedCard({ pickedFile, edited, onEdit, onRemove }) {
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
			</div>
			{onEdit && pickedFile.kind === 'image' && (
				<button
					type="button"
					onClick={onEdit}
					aria-label={`Crop or rotate ${pickedFile.file.name}`}
					className="absolute right-12 top-2.5 grid size-8 place-items-center rounded-full bg-black/55 text-white backdrop-blur transition hover:bg-accent sm:opacity-0 sm:group-hover:opacity-100 sm:focus-visible:opacity-100"
				>
					<Icon name="crop" className="size-4" />
				</button>
			)}
			<button
				type="button"
				onClick={onRemove}
				aria-label={`Remove ${pickedFile.file.name}`}
				className="absolute right-2.5 top-2.5 grid size-8 place-items-center rounded-full bg-black/55 text-white backdrop-blur transition hover:bg-bad sm:opacity-0 sm:group-hover:opacity-100 sm:focus-visible:opacity-100"
			>
				<Icon name="x" className="size-4" />
			</button>
			<div className="absolute inset-x-0 bottom-0 p-3.5 text-white">
				<p className="truncate text-sm font-semibold" title={pickedFile.file.name}>{pickedFile.file.name}</p>
				<p className="tnum truncate text-xs text-white/75">{fmtBytes(pickedFile.file.size)}{meta && ` · ${meta}`}</p>
			</div>
		</CardShell>
	)
}