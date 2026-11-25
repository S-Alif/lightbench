import { useCallback, useEffect, useRef, useState } from 'react'
import { api } from '../api/client.js'
import Icon from '../components/icons/Icon.jsx'
import { btn } from '../components/ui/buttonStyles.js'
import { Field } from '../components/ui/Field.jsx'
import { Seg } from '../components/ui/Seg.jsx'
import { Switch } from '../components/ui/Switch.jsx'
import { useToast } from '../components/ui/Toast.jsx'
import { DEFAULT_PRESET, PRESETS, SLIDERS } from '../features/vectorizer/presets.js'
import { copyText } from '../lib/clipboard.js'
import { takeVectorizeHandoff } from '../lib/vectorizeHandoff.js'

const fmtBytes = (bytes) => bytes > 1048576 ? `${(bytes / 1048576).toFixed(1)} MB` : `${Math.max(1, Math.round(bytes / 1024))} KB`
const checkerboard = { backgroundImage: 'conic-gradient(#8883 25%, transparent 0 50%, #8883 0 75%, transparent 0)', backgroundSize: '20px 20px' }

export default function VectorizePage() {
	const toast = useToast()
	const [file, setFile] = useState(() => takeVectorizeHandoff())
	const [originalUrl, setOriginalUrl] = useState('')
	const [presetKey, setPresetKey] = useState(DEFAULT_PRESET)
	const [options, setOptions] = useState({ ...PRESETS[DEFAULT_PRESET].options, keep_transparency: true })
	const [result, setResult] = useState(null)
	const [vectorUrl, setVectorUrl] = useState('')
	const [busy, setBusy] = useState(false)
	const [error, setError] = useState('')
	const [view, setView] = useState('split')
	const [dragging, setDragging] = useState(false)
	const inputRef = useRef(null)

	// preview url for the original image
	useEffect(() => {
		if (!file) { setOriginalUrl(''); return }
		const url = URL.createObjectURL(file)
		setOriginalUrl(url)
		return () => URL.revokeObjectURL(url)
	}, [file])

	// preview url for the svg
	useEffect(() => {
		if (!result) { setVectorUrl(''); return }
		const url = URL.createObjectURL(new Blob([result.svg], { type: 'image/svg+xml' }))
		setVectorUrl(url)
		return () => URL.revokeObjectURL(url)
	}, [result])

	// re-trace shortly after the file or any option changes; a newer change cancels the older request
	useEffect(() => {
		if (!file) return
		const controller = new AbortController()
		const timer = setTimeout(async () => {
			setBusy(true)
			setError('')
			try {
				setResult(await api.vectorize(file, options, controller.signal))
				setBusy(false)
			} catch (traceError) {
				if (traceError.name === 'AbortError') return
				setError(traceError.message)
				setBusy(false)
			}
		}, 450)
		return () => { clearTimeout(timer); controller.abort() }
	}, [file, options])

	const pickFile = useCallback((picked) => {
		if (!picked) return
		if (!picked.type.startsWith('image/')) { toast('Please choose an image'); return }
		setResult(null)
		setFile(picked)
	}, [toast])

	const applyPreset = (key) => { setPresetKey(key); setOptions((current) => ({ ...PRESETS[key].options, keep_transparency: current.keep_transparency })) }
	const changeOption = (key, value) => { setPresetKey(''); setOptions((current) => ({ ...current, [key]: value })) }

	const download = () => {
		const link = document.createElement('a')
		link.href = vectorUrl
		link.download = `${(file?.name || 'image').replace(/\.[^.]+$/, '')}.svg`
		link.click()
	}

	const dropProps = {
		onDragOver: (event) => { event.preventDefault(); setDragging(true) },
		onDragLeave: () => setDragging(false),
		onDrop: (event) => { event.preventDefault(); setDragging(false); pickFile(event.dataTransfer.files?.[0]) },
	}

	const imageBox = (src, label, withChecker) => (
		<figure className="min-w-0 flex-1">
			<figcaption className="mb-2 text-xs font-semibold uppercase tracking-wide text-muted">{label}</figcaption>
			<div className="grid min-h-64 place-items-center overflow-hidden rounded-2xl bg-sunken p-3 ring-1 ring-line" style={withChecker ? checkerboard : undefined}>
				{src ? <img src={src} alt={label} className="max-h-[70vh] max-w-full object-contain" /> : <span className="text-sm text-muted">{busy ? 'Tracing…' : '—'}</span>}
			</div>
		</figure>
	)

	return (
		<div className="space-y-6">
			<div>
				<h1 className="text-2xl font-semibold tracking-tight">Vectorizer</h1>
				<p className="mt-1 text-sm text-muted">Turn a picture into a crisp SVG that works on the web and in design apps. Nothing is saved on the server.</p>
			</div>

			{!file ? (
				<button type="button" onClick={() => inputRef.current?.click()} {...dropProps}
					className={`grid h-72 w-full place-items-center rounded-3xl border-2 border-dashed text-center transition ${dragging ? 'border-accent bg-accent/10' : 'border-line bg-surface hover:bg-sunken'}`}>
					<span className="space-y-2">
						<Icon name="upload" className="mx-auto size-8 text-muted" />
						<span className="block font-medium">Drop an image here or click to choose</span>
						<span className="block text-sm text-muted">PNG, JPG, WebP and more</span>
					</span>
				</button>
			) : (
				<div className="grid gap-6 lg:grid-cols-[20rem_1fr]" {...dropProps}>
					{/* controls */}
					<aside className="space-y-5 rounded-3xl bg-surface p-5 ring-1 ring-line">
						<Field label="Style" hint={PRESETS[presetKey]?.hint || 'Custom'}>
							<div className="grid grid-cols-2 gap-2">
								{Object.entries(PRESETS).map(([key, preset]) => (
									<button key={key} type="button" onClick={() => applyPreset(key)}
										className={`h-10 rounded-xl px-2 text-sm font-medium transition ${presetKey === key ? 'bg-accent text-accent-ink' : 'bg-sunken text-muted hover:text-ink'}`}>
										{preset.label}
									</button>
								))}
							</div>
						</Field>

						{SLIDERS.filter(([key]) => !(options.colormode === 'binary' && ['colors', 'gradient_steps'].includes(key))).map(([key, label, min, max, step, hint]) => (
							<Field key={key} label={label} hint={`${options[key]} · ${hint}`}>
								<input type="range" min={min} max={max} step={step} value={options[key]} aria-label={label}
									onChange={(event) => changeOption(key, Number(event.target.value))} className="w-full accent-(--color-accent)" />
							</Field>
						))}

						<Field label="Curves">
							<Seg label="Curves" value={options.curves} onChange={(value) => changeOption('curves', value)}
								options={[['spline', 'Smooth'], ['polygon', 'Straight'], ['pixel', 'Pixel']]} />
						</Field>
						<Field label="Layers" hint={options.layering === 'stacked' ? 'smaller file' : 'no overlapping shapes'}>
							<Seg label="Layers" value={options.layering} onChange={(value) => changeOption('layering', value)}
								options={[['stacked', 'Stacked'], ['cutout', 'Cut-out']]} />
						</Field>
						<Switch checked={options.keep_transparency} onChange={(value) => changeOption('keep_transparency', value)} title="Keep transparent background" />

						<div className="flex gap-2 border-t border-line pt-4">
							<button type="button" onClick={() => inputRef.current?.click()} className={btn('secondary', 'sm', 'flex-1')}><Icon name="image" className="size-4" />Change image</button>
						</div>
					</aside>

					{/* preview */}
					<section className="order-first min-w-0 space-y-4 lg:order-0">
						<div className="flex flex-wrap items-center gap-3">
							<div className="w-full max-w-sm"><Seg label="Preview" value={view} onChange={setView} options={[['original', 'Original'], ['split', 'Side by side'], ['vector', 'Vector']]} /></div>
							<div className="ml-auto flex flex-wrap gap-2">
								<button type="button" disabled={!result} onClick={async () => toast((await copyText(result.svg)) ? 'SVG code copied' : 'Could not copy')} className={btn('secondary', 'sm')}><Icon name="copy" className="size-4" />Copy SVG</button>
								<button type="button" disabled={!result} onClick={download} className={btn('primary', 'sm')}><Icon name="download" className="size-4" />Download SVG</button>
							</div>
						</div>

						{error && <p role="alert" className="rounded-xl bg-bad/10 px-4 py-3 text-sm text-bad">{error}</p>}

						<div className={`flex gap-4 ${view === 'split' ? 'flex-col md:flex-row' : ''}`}>
							{view !== 'vector' && imageBox(originalUrl, 'Original', false)}
							{view !== 'original' && imageBox(vectorUrl, busy && result ? 'Vector (updating…)' : 'Vector', true)}
						</div>

						{result && (
							<p className="tnum text-sm text-muted">
								{result.width}×{result.height} · {result.paths.toLocaleString()} shapes · {fmtBytes(result.bytes)} · original {fmtBytes(file.size)}
							</p>
						)}
					</section>
				</div>
			)}
			<input ref={inputRef} type="file" accept="image/*" hidden onChange={(event) => { pickFile(event.target.files?.[0]); event.target.value = '' }} />
		</div>
	)
}
