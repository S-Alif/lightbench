import { useState } from 'react'
import { api } from '../../api/client.js'
import Icon from '../../components/icons/Icon.jsx'
import { btn } from '../../components/ui/buttonStyles.js'
import { Field } from '../../components/ui/Field.jsx'
import { Seg } from '../../components/ui/Seg.jsx'
import { downloadBlob } from '../../lib/zip.js'
import { NumberBox } from '../settings/controls.jsx'
import { folderMissing, saveTarget } from './SaveTo.jsx'

export const SPLIT_DEFAULTS = { rows: 2, columns: 3, fmt: 'png', quality: 92 }

// cuts one picture into equal tiles (sprite sheets, carousel posts, puzzle pieces)
export function SplitPanel({ entry, options, setOptions, save, local }) {
	const [busy, setBusy] = useState(false)
	const [message, setMessage] = useState({ text: '', bad: false })
	const set = (patch) => { setMessage({ text: '', bad: false }); setOptions((current) => ({ ...current, ...patch })) }
	const rows = Math.min(20, Math.max(1, options.rows)), columns = Math.min(20, Math.max(1, options.columns))

	const run = async () => {
		setBusy(true)
		setMessage({ text: '', bad: false })
		try {
			const folder = saveTarget(save, local)
			const answer = await api.toolsSplit(entry.file, folder ? { ...options, save_to: folder } : options)
			if (answer.blob) { downloadBlob(answer.blob, `${entry.file.name.replace(/\.[^.]+$/, '')}-tiles.zip`); setMessage({ text: `${rows * columns} tiles downloaded as a .zip`, bad: false }) }
			else setMessage({ text: `Saved ${answer.info.saved.length} tiles to ${answer.info.saved[0].replace(/[\\/][^\\/]*$/, '')}`, bad: false })
		} catch (failure) { setMessage({ text: failure.message, bad: true }) }
		setBusy(false)
	}

	return (
		<div className="grid gap-6 md:grid-cols-[18rem_1fr]">
			<div className="space-y-5">
				<div className="grid grid-cols-2 gap-3">
					<NumberBox label="Rows" value={options.rows} onChange={(value) => set({ rows: value })} suffix="" />
					<NumberBox label="Columns" value={options.columns} onChange={(value) => set({ columns: value })} suffix="" />
				</div>
				<Field label="Format"><Seg label="Format" value={options.fmt} onChange={(fmt) => set({ fmt })} options={[['png', 'PNG'], ['jpg', 'JPG'], ['webp', 'WebP']]} /></Field>
				<button type="button" disabled={!entry || busy || rows * columns < 2 || folderMissing(save, local)} onClick={run} className={`${btn('primary', 'md')} w-full`}><Icon name="download" className="size-4" />{busy ? 'Working…' : `Cut into ${rows * columns} tiles`}</button>
				{message.text && <p role={message.bad ? 'alert' : 'status'} className={`text-sm ${message.bad ? 'text-bad' : 'text-ok'}`}>{message.text}</p>}
			</div>
			<div className="grid place-items-center rounded-2xl bg-sunken p-3 ring-1 ring-line">
				{entry && (
					<div className="relative inline-block leading-none">
						<img src={entry.url} alt="Preview" className="max-h-[60vh] max-w-full" />
						<div className="pointer-events-none absolute inset-0">
							{Array.from({ length: columns - 1 }, (_, index) => <span key={`c${index}`} className="absolute inset-y-0 w-px bg-white mix-blend-difference" style={{ left: `${((index + 1) / columns) * 100}%` }} />)}
							{Array.from({ length: rows - 1 }, (_, index) => <span key={`r${index}`} className="absolute inset-x-0 h-px bg-white mix-blend-difference" style={{ top: `${((index + 1) / rows) * 100}%` }} />)}
						</div>
					</div>
				)}
			</div>
		</div>
	)
}
