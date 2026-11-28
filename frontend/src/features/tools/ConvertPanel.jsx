import { useRef, useState } from 'react'
import { api } from '../../api/client.js'
import Icon from '../../components/icons/Icon.jsx'
import { btn } from '../../components/ui/buttonStyles.js'
import { Field } from '../../components/ui/Field.jsx'
import { ProgressBar } from '../../components/ui/ProgressBar.jsx'
import { Seg } from '../../components/ui/Seg.jsx'
import { downloadBlob, makeZip, uniqueNames } from '../../lib/zip.js'
import { fmtBytes, plural } from '../../lib/format.js'
import { NumberBox, Slider } from '../settings/controls.jsx'
import { folderMissing, saveTarget } from './SaveTo.jsx'

export const CONVERT_DEFAULTS = {
	fmt: 'keep', quality: 85, target_kb: 0, resize: 'none', percent: 50, width: 1920, height: 0, metadata: 'remove_all',
	brightness: 0, contrast: 0, saturation: 0, sharpen: 0, background: '#ffffff',
}

const percentOf = (before, after) => (before ? Math.round((1 - after / before) * 100) : 0)

// convert / resize / compress / colour / clean metadata, one request per picture so progress is real
export function ConvertPanel({ files, options, setOptions, save, local }) {
	const [running, setRunning] = useState(null)   // { done, total }
	const [results, setResults] = useState([])     // { name, ok, blob, info, before, error }
	const controller = useRef(null)
	const set = (patch) => setOptions((current) => ({ ...current, ...patch }))
	const colourChanged = options.brightness || options.contrast || options.saturation || options.sharpen

	const run = async () => {
		const abort = new AbortController()
		controller.current = abort
		const folder = saveTarget(save, local)
		const sent = { ...options }
		if (sent.resize !== 'fit') { delete sent.width; delete sent.height }
		if (folder) sent.save_to = folder
		setResults([])
		const collected = []
		for (let index = 0; index < files.length; index++) {
			setRunning({ done: index, total: files.length })
			const { file } = files[index]
			try {
				const answer = await api.toolsConvert(file, sent, abort.signal)
				collected.push({ name: file.name, ok: true, blob: answer.blob, info: answer.info, before: file.size })
			} catch (failure) {
				if (failure.name === 'AbortError') break
				collected.push({ name: file.name, ok: false, error: failure.message, before: file.size })
			}
			setResults([...collected])
		}
		setRunning(null)
	}

	const good = results.filter((result) => result.ok)
	const folderUsed = good.length > 0 && good[0].info.saved
	const outNames = uniqueNames(good.map((result) => (result.info.saved ? '' : `${result.name.replace(/\.[^.]+$/, '')}.${result.info.ext}`)))
	const downloadAll = async () => {
		if (good.length === 1) return downloadBlob(good[0].blob, outNames[0])
		downloadBlob(await makeZip(good.map((result, index) => ({ name: outNames[index], blob: result.blob }))), 'lightbench-converted.zip')
	}
	const totalBefore = good.reduce((sum, result) => sum + result.before, 0)
	const totalAfter = good.reduce((sum, result) => sum + (result.info.bytes ?? result.blob.size), 0)

	return (
		<div className="space-y-6">
			<div className="grid gap-6 md:grid-cols-2">
				<div className="space-y-5">
					<Field label="Format">
						<Seg label="Format" value={options.fmt} onChange={(fmt) => set({ fmt })} options={[['keep', 'Same'], ['jpg', 'JPG'], ['png', 'PNG'], ['webp', 'WebP']]} />
					</Field>
					{options.fmt !== 'png' && (
						<Field label="File size" hint="JPG and WebP">
							<Slider label="Quality" min={10} max={100} value={options.quality} onChange={(quality) => set({ quality })} />
							<NumberBox label="Or aim for at most (0 = off)" value={options.target_kb} onChange={(target_kb) => set({ target_kb })} step={50} suffix="KB" />
						</Field>
					)}
					{options.fmt === 'jpg' && (
						<Field label="Transparent areas become">
							<input type="color" value={options.background} onChange={(event) => set({ background: event.target.value })} aria-label="Background colour" className="h-10 w-full cursor-pointer rounded-xl bg-sunken p-1 ring-1 ring-line" />
						</Field>
					)}
					<Field label="Size">
						<Seg label="Resize" value={options.resize} onChange={(resize) => set({ resize })} options={[['none', 'Original'], ['percent', 'Percent'], ['fit', 'Fit in box']]} />
						{options.resize === 'percent' && <Slider label="Scale" min={5} max={200} value={options.percent} onChange={(percent) => set({ percent })} format={(value) => `${value}%`} />}
						{options.resize === 'fit' && (
							<div className="grid grid-cols-2 gap-3">
								<NumberBox label="Max width (0 = any)" value={options.width} onChange={(width) => set({ width })} suffix="px" />
								<NumberBox label="Max height (0 = any)" value={options.height} onChange={(height) => set({ height })} suffix="px" />
							</div>
						)}
						{options.resize === 'fit' && <p className="text-xs text-muted">Only shrinks. Smaller pictures stay as they are.</p>}
					</Field>
				</div>

				<div className="space-y-5">
					<Field label="Privacy" hint="what is hidden inside a photo">
						<Seg label="Metadata" value={options.metadata} onChange={(metadata) => set({ metadata })} options={[['remove_all', 'Remove all'], ['remove_location', 'Only location'], ['keep', 'Keep']]} />
						<p className="text-xs text-muted">
							{options.metadata === 'remove_all' ? 'Camera, date, GPS location and generation prompts are removed. The colour profile stays so colours do not change.'
								: options.metadata === 'remove_location' ? 'Only the GPS position is removed. Camera and date stay.' : 'Everything is kept as it was.'}
						</p>
					</Field>
					<Field label="Colour" hint={colourChanged ? undefined : 'untouched'}>
						<Slider label="Brightness" min={-100} max={100} value={options.brightness} onChange={(brightness) => set({ brightness })} />
						<Slider label="Contrast" min={-100} max={100} value={options.contrast} onChange={(contrast) => set({ contrast })} />
						<Slider label="Saturation" min={-100} max={100} value={options.saturation} onChange={(saturation) => set({ saturation })} />
						<Slider label="Sharpen" min={0} max={100} value={options.sharpen} onChange={(sharpen) => set({ sharpen })} />
						{colourChanged ? <button type="button" onClick={() => set({ brightness: 0, contrast: 0, saturation: 0, sharpen: 0 })} className={btn('ghost', 'sm')}>Reset colour</button> : null}
					</Field>
				</div>
			</div>

			<div className="flex flex-wrap items-center gap-3">
				{running ? (
					<button type="button" onClick={() => controller.current?.abort()} className={btn('secondary', 'md')}>Cancel</button>
				) : (
					<button type="button" disabled={!files.length || folderMissing(save, local)} onClick={run} className={btn('primary', 'md')}>
						<Icon name="refresh" className="size-4" />Convert {plural(files.length, 'picture')}
					</button>
				)}
				{running && <div className="min-w-48 flex-1"><ProgressBar value={running.done / running.total} /><p className="tnum mt-1 text-xs text-muted">{running.done + 1} of {running.total}</p></div>}
			</div>

			{results.length > 0 && (
				<div className="space-y-3">
					<ul className="divide-y divide-line rounded-2xl bg-surface ring-1 ring-line">
						{results.map((result, index) => (
							<li key={index} className="flex flex-wrap items-center gap-x-4 gap-y-1 px-4 py-3 text-sm">
								<span className="min-w-0 flex-1 truncate font-medium" title={result.name}>{result.name}</span>
								{result.ok ? (
									<span className="tnum text-muted">
										{fmtBytes(result.before)} → <b className="text-ink">{fmtBytes(result.info.bytes ?? result.blob.size)}</b>
										{' '}({percentOf(result.before, result.info.bytes ?? result.blob.size) >= 0 ? '−' : '+'}{Math.abs(percentOf(result.before, result.info.bytes ?? result.blob.size))}%) · {result.info.width}×{result.info.height}
										{result.info.saved ? ` · saved as ${result.info.saved[0].split(/[\\/]/).pop()}` : ''}
									</span>
								) : <span className="text-bad">{result.error}</span>}
								{result.ok && result.info.note && <span className="w-full text-xs text-muted">{result.info.note}</span>}
							</li>
						))}
					</ul>
					{good.length > 0 && !running && (
						<div className="flex flex-wrap items-center gap-3">
							{folderUsed ? <p className="text-sm text-ok">Saved {plural(good.length, 'file')} to {good[0].info.saved[0].replace(/[\\/][^\\/]*$/, '')}</p> : (
								<button type="button" onClick={downloadAll} className={btn('primary', 'md')}><Icon name="download" className="size-4" />{good.length === 1 ? 'Download' : `Download ${good.length} as .zip`}</button>
							)}
							{good.length > 1 && <span className="tnum text-sm text-muted">Total {fmtBytes(totalBefore)} → {fmtBytes(totalAfter)}</span>}
						</div>
					)}
				</div>
			)}
		</div>
	)
}
