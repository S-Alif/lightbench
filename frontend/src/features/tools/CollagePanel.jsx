import { useEffect, useRef, useState } from 'react'
import { api } from '../../api/client.js'
import Icon from '../../components/icons/Icon.jsx'
import { btn } from '../../components/ui/buttonStyles.js'
import { Field } from '../../components/ui/Field.jsx'
import { Seg } from '../../components/ui/Seg.jsx'
import { Switch } from '../../components/ui/Switch.jsx'
import { downloadBlob } from '../../lib/zip.js'
import { fmtBytes } from '../../lib/format.js'
import { Slider } from '../settings/controls.jsx'
import { folderMissing, saveTarget } from './SaveTo.jsx'

export const COLLAGE_DEFAULTS = { columns: 0, cell_width: 600, ratio: '1:1', fit: 'cover', gap: 12, margin: 12, background: '#ffffff', transparent: false, fmt: 'jpg', quality: 90 }
const RATIOS = ['1:1', '4:3', '3:4', '3:2', '2:3', '16:9', '9:16']

// several pictures in one grid
export function CollagePanel({ files, options, setOptions, save, local }) {
	const [busy, setBusy] = useState(false)
	const [error, setError] = useState('')
	const [result, setResult] = useState(null)   // { blob, url, info }
	const controller = useRef(null)
	const set = (patch) => setOptions((current) => ({ ...current, ...patch }))
	useEffect(() => () => { if (result?.url) URL.revokeObjectURL(result.url) }, [result])
	useEffect(() => { setResult(null) }, [files, options])

	const make = async () => {
		controller.current = new AbortController()
		setBusy(true)
		setError('')
		try {
			const folder = saveTarget(save, local)
			const answer = await api.toolsCollage(files.map((entry) => entry.file), folder ? { ...options, save_to: folder } : options, controller.current.signal)
			setResult({ blob: answer.blob, url: answer.blob ? URL.createObjectURL(answer.blob) : '', info: answer.info })
		} catch (failure) {
			if (failure.name !== 'AbortError') setError(failure.message)
		}
		setBusy(false)
	}

	return (
		<div className="space-y-6">
			<div className="grid gap-6 md:grid-cols-2">
				<div className="space-y-5">
					<Field label="Columns" hint={options.columns ? undefined : 'chosen automatically'}>
						<Slider label="Columns" min={0} max={8} value={options.columns} onChange={(columns) => set({ columns })} format={(value) => (value || 'Auto')} />
					</Field>
					<Field label="Each picture">
						<select value={options.ratio} onChange={(event) => set({ ratio: event.target.value })} aria-label="Shape" className="h-11 w-full rounded-xl bg-surface px-3 text-[15px] ring-1 ring-line">
							{RATIOS.map((ratio) => <option key={ratio} value={ratio}>{ratio}</option>)}
						</select>
						<Seg label="Fit" value={options.fit} onChange={(fit) => set({ fit })} options={[['cover', 'Fill (crop)'], ['contain', 'Show whole']]} />
						<Slider label="Size" min={200} max={1200} step={50} value={options.cell_width} onChange={(cell_width) => set({ cell_width })} format={(value) => `${value}px`} />
					</Field>
				</div>
				<div className="space-y-5">
					<Field label="Spacing">
						<Slider label="Gap" min={0} max={80} value={options.gap} onChange={(gap) => set({ gap })} format={(value) => `${value}px`} />
						<Slider label="Margin" min={0} max={120} value={options.margin} onChange={(margin) => set({ margin })} format={(value) => `${value}px`} />
					</Field>
					<Field label="Background">
						<input type="color" value={options.background} disabled={options.transparent} onChange={(event) => set({ background: event.target.value })} aria-label="Background colour" className="h-10 w-full cursor-pointer rounded-xl bg-sunken p-1 ring-1 ring-line disabled:opacity-40" />
						<Switch checked={options.transparent} onChange={(transparent) => set({ transparent, fmt: transparent ? 'png' : options.fmt })} title="Transparent" hint="Saved as PNG" />
					</Field>
					<Field label="Format">
						<Seg label="Format" value={options.fmt} onChange={(fmt) => set({ fmt })} disabled={options.transparent} options={[['jpg', 'JPG'], ['png', 'PNG']]} />
					</Field>
				</div>
			</div>

			<div className="flex flex-wrap items-center gap-3">
				<button type="button" disabled={files.length < 2 || busy || folderMissing(save, local)} onClick={make} className={btn('primary', 'md')}><Icon name="image" className="size-4" />{busy ? 'Working…' : 'Make collage'}</button>
				{files.length < 2 && <span className="text-sm text-muted">Add at least two pictures.</span>}
			</div>
			{error && <p role="alert" className="rounded-xl bg-bad/10 px-4 py-3 text-sm text-bad">{error}</p>}
			{result && (
				<div className="space-y-3">
					{result.blob ? (
						<>
							<div className="overflow-hidden rounded-2xl bg-sunken p-3 ring-1 ring-line"><img src={result.url} alt="Collage" className="mx-auto max-h-[70vh] max-w-full object-contain" /></div>
							<div className="flex flex-wrap items-center gap-3">
								<button type="button" onClick={() => downloadBlob(result.blob, `collage.${result.info.ext}`)} className={btn('primary', 'md')}><Icon name="download" className="size-4" />Download</button>
								<span className="tnum text-sm text-muted">{result.info.width}×{result.info.height} · {fmtBytes(result.blob.size)}</span>
							</div>
						</>
					) : <p className="text-sm text-ok">Saved as {result.info.saved[0]}</p>}
				</div>
			)}
		</div>
	)
}
