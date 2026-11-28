import Icon from '../../components/icons/Icon.jsx'
import { fmtBytes } from '../../lib/format.js'

// the picked pictures as small tiles, with remove and (for the collage) move buttons
export function FileStrip({ files, onRemove, onMove }) {
	return (
		<ul className="flex gap-3 overflow-x-auto pb-1">
			{files.map((entry, index) => (
				<li key={entry.id} className="relative w-28 shrink-0">
					<img src={entry.url} alt={entry.file.name} className="size-28 rounded-xl bg-sunken object-cover ring-1 ring-line" />
					<p className="mt-1 truncate text-xs" title={entry.file.name}>{entry.file.name}</p>
					<p className="tnum text-xs text-muted">{fmtBytes(entry.file.size)}</p>
					<button type="button" onClick={() => onRemove(entry.id)} aria-label={`Remove ${entry.file.name}`}
						className="absolute right-1 top-1 grid size-6 place-items-center rounded-full bg-black/65 text-white hover:bg-black"><Icon name="x" className="size-3.5" /></button>
					{onMove && files.length > 1 && (
						<div className="absolute bottom-[3.25rem] left-1 flex gap-1">
							<button type="button" disabled={index === 0} onClick={() => onMove(index, -1)} aria-label="Move earlier" className="grid size-6 place-items-center rounded-full bg-black/65 text-white disabled:opacity-30"><Icon name="left" className="size-3.5" /></button>
							<button type="button" disabled={index === files.length - 1} onClick={() => onMove(index, 1)} aria-label="Move later" className="grid size-6 place-items-center rounded-full bg-black/65 text-white disabled:opacity-30"><Icon name="right" className="size-3.5" /></button>
						</div>
					)}
				</li>
			))}
		</ul>
	)
}
