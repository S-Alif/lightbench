import { useLayoutEffect, useMemo, useRef, useState } from 'react'
import Icon from '../../components/icons/Icon.jsx'
import { btn } from '../../components/ui/buttonStyles.js'
import { Modal } from '../../components/ui/Modal.jsx'
import { RATIO_PRESETS, platformName, ratioLabel } from './cropPresets.js'
import { FULL_CROP, MAX_STRAIGHTEN, NO_ADJUST, adjustFilter, fitRatio, hasAdjust, isFullCrop, mirrorCrop, moveCrop, resizeCrop, rotatedSize, rotationAfterFlip, straightenScale, straightenedSize, toEdit, turn } from './editMath.js'

// where each resize handle sits on the crop box, as percentages
const HANDLES = {
	nw: ['0%', '0%'], n: ['50%', '0%'], ne: ['100%', '0%'],
	w: ['0%', '50%'], e: ['100%', '50%'],
	sw: ['0%', '100%'], s: ['50%', '100%'], se: ['100%', '100%'],
}
const CURSORS = { nw: 'nwse-resize', se: 'nwse-resize', ne: 'nesw-resize', sw: 'nesw-resize', n: 'ns-resize', s: 'ns-resize', e: 'ew-resize', w: 'ew-resize' }

// a labelled slider with its value on the right. double click returns it to zero
function Slider({ id, label, value, min, max, step, disabled, onChange, format = (number) => (number > 0 ? `+${number}` : String(number)) }) {
	return (
		<div>
			<div className="mb-1.5 flex items-baseline justify-between">
				<label htmlFor={id} className="text-sm font-medium">{label}</label>
				<span className={`tnum text-sm ${value ? 'text-ink' : 'text-muted'}`}>{format(value)}</span>
			</div>
			<input
				id={id}
				type="range"
				min={min}
				max={max}
				step={step}
				value={value}
				disabled={disabled}
				onChange={(changeEvent) => onChange(Number(changeEvent.target.value))}
				onDoubleClick={() => onChange(0)}
				className="h-2 w-full cursor-pointer accent-accent"
			/>
		</div>
	)
}

// how big the element is, kept up to date while the window or panel changes size
function useElementSize() {
	const ref = useRef(null)
	const [size, setSize] = useState({ width: 0, height: 0 })
	useLayoutEffect(() => {
		const element = ref.current
		if (!element) return undefined
		const observer = new ResizeObserver(([entry]) => setSize({ width: entry.contentRect.width, height: entry.contentRect.height }))
		observer.observe(element)
		return () => observer.disconnect()
	}, [])
	return [ref, size]
}

// a tiny drawing of a crop shape
function ShapeGlyph({ width, height, dashed = false }) {
	const longest = Math.max(width, height)
	return (
		<span className="grid size-8 place-items-center">
			<span className={`block rounded-[3px] border-2 border-current ${dashed ? 'border-dashed' : ''}`} style={{ width: Math.round((24 * width) / longest), height: Math.round((24 * height) / longest) }} />
		</span>
	)
}

function ShapeTile({ selected, disabled, onClick, glyph, title, subtitle }) {
	return (
		<button
			type="button"
			onClick={onClick}
			disabled={disabled}
			aria-pressed={selected}
			className={`flex min-h-[5.75rem] flex-col items-center justify-start gap-1 rounded-2xl px-1.5 py-2.5 text-center transition disabled:opacity-50 ${selected ? 'bg-accent/12 text-accent ring-2 ring-accent' : 'text-ink ring-1 ring-line hover:bg-sunken'}`}
		>
			{glyph}
			<span className="text-sm font-semibold leading-none">{title}</span>
			{subtitle && <span className="text-[11px] leading-tight text-muted">{subtitle}</span>}
		</button>
	)
}

function ActionButton({ icon, label, onClick, disabled }) {
	return (
		<button type="button" onClick={onClick} disabled={disabled} aria-label={label} className="flex flex-col items-center gap-2 rounded-2xl px-2 py-4 text-sm font-medium ring-1 ring-line transition hover:bg-sunken disabled:opacity-50">
			<Icon name={icon} className="size-6" />{label}
		</button>
	)
}

const TABS = [['crop', 'Crop'], ['rotate', 'Rotate'], ['colour', 'Colour']]

// ---- the basic editor: crop, rotate, flip, straighten and colour for one image ----------------------------
export function CropEditor({ pickedFile, edit, onApply, onClose, applyLabel = 'Apply', note = '' }) {
	const [naturalSize, setNaturalSize] = useState(null)
	const [rotate, setRotate] = useState(edit?.rotate || 0)
	const [straighten, setStraighten] = useState(edit?.straighten || 0)   // small extra turn in degrees, clockwise
	const [adjust, setAdjust] = useState({ ...NO_ADJUST, ...(edit?.adjust || {}) })   // brightness, contrast, saturation: -100 to 100
	const [flip, setFlip] = useState(Boolean(edit?.flip))      // mirrored left to right before the turn
	const [crop, setCrop] = useState(edit?.crop || FULL_CROP)
	const [presetId, setPresetId] = useState('free')      // 'free' is free roam
	const [swapped, setSwapped] = useState(false)
	const [tab, setTab] = useState('crop')
	const [areaRef, area] = useElementSize()      // the space the picture may use
	const stageRef = useRef(null)
	const drag = useRef(null)

	const rotated = naturalSize ? rotatedSize(naturalSize.width, naturalSize.height, rotate) : null
	// the picture the crop box lives on: turned, then straightened (same shape, fewer pixels)
	const turned = rotated ? straightenedSize(rotated.width, rotated.height, straighten) : null

	// the fixed shape being kept, or null for free roam
	const ratio = useMemo(() => {
		if (!turned || presetId === 'free') return null
		const preset = RATIO_PRESETS.find((candidate) => candidate.id === presetId)
		const base = preset.ratio === 'original' ? turned : preset
		return swapped ? { width: base.height, height: base.width } : { width: base.width, height: base.height }
	}, [turned?.width, turned?.height, presetId, swapped])

	const refit = (nextRatio, size) => setCrop(nextRatio ? fitRatio(nextRatio.width, nextRatio.height, size.width, size.height) : FULL_CROP)

	const choosePreset = (id) => {
		setPresetId(id)
		setSwapped(false)
		if (id === 'free') return
		const preset = RATIO_PRESETS.find((candidate) => candidate.id === id)
		const base = preset.ratio === 'original' ? turned : preset
		refit({ width: base.width, height: base.height }, turned)
	}

	const swapShape = () => {
		setSwapped(!swapped)
		refit({ width: ratio.height, height: ratio.width }, turned)
	}

	const rotateBy = (direction) => {
		const nextRotate = turn(rotate, direction)
		const nextRotated = rotatedSize(naturalSize.width, naturalSize.height, nextRotate)
		const nextTurned = straightenedSize(nextRotated.width, nextRotated.height, straighten)
		setRotate(nextRotate)
		// a crop made before turning no longer lines up, so start it again
		if (presetId === 'free') { setCrop(FULL_CROP); return }
		const preset = RATIO_PRESETS.find((candidate) => candidate.id === presetId)
		const base = preset.ratio === 'original' ? nextTurned : preset
		refit(swapped ? { width: base.height, height: base.width } : { width: base.width, height: base.height }, nextTurned)
	}

	const flipView = (vertical) => {
		setRotate(rotationAfterFlip(rotate, vertical))
		setFlip(!flip)
		setCrop(mirrorCrop(crop, vertical))
	}

	const reset = () => { setRotate(0); setFlip(false); setStraighten(0); setAdjust(NO_ADJUST); setCrop(FULL_CROP); setPresetId('free'); setSwapped(false) }

	// ---- dragging ----
	const pointerFraction = (pointerEvent) => {
		const box = stageRef.current.getBoundingClientRect()
		return { x: (pointerEvent.clientX - box.left) / box.width, y: (pointerEvent.clientY - box.top) / box.height }
	}
	const startDrag = (pointerEvent, handle) => {
		pointerEvent.preventDefault()
		pointerEvent.stopPropagation()
		pointerEvent.currentTarget.setPointerCapture(pointerEvent.pointerId)
		drag.current = { handle, startCrop: crop, startPointer: pointerFraction(pointerEvent) }
	}
	const moveDrag = (pointerEvent) => {
		const current = drag.current
		if (!current) return
		const pointer = pointerFraction(pointerEvent)
		if (current.handle === 'move') setCrop(moveCrop(current.startCrop, pointer.x - current.startPointer.x, pointer.y - current.startPointer.y))
		else setCrop(resizeCrop(current.startCrop, current.handle, pointer, turned, ratio))
	}
	const endDrag = () => { drag.current = null }

	const cropWidthPixels = turned ? Math.max(1, Math.round(crop.width * turned.width)) : 0
	const cropHeightPixels = turned ? Math.max(1, Math.round(crop.height * turned.height)) : 0
	const shapeText = ratio ? ratioLabel(ratio.width, ratio.height) : 'Free roam'
	const visibleHandles = Object.keys(HANDLES).filter((name) => !ratio || name.length === 2)

	const changed = { crop: !isFullCrop(crop), rotate: rotate !== 0 || flip || straighten !== 0, colour: hasAdjust(adjust) }

	// the picture, as big as the free space allows
	const fit = rotated && area.width > 0 ? Math.min(area.width / rotated.width, area.height / rotated.height) : 0
	const stageStyle = rotated ? { width: Math.max(1, rotated.width * fit), height: Math.max(1, rotated.height * fit) } : null

	return (
		<Modal open onClose={onClose} label="Basic editor" size="2xl" padded={false}>
			{/* the panel always fits the screen: picture on top and tools below on phones, side by side on wide screens */}
				<div className="flex h-[calc(100dvh-2rem)] flex-col sm:h-[calc(100dvh-4rem)] lg:h-[min(88vh,800px)] lg:flex-row">
				{/* the picture */}
				<div className="flex h-[38%] min-w-0 shrink-0 flex-col bg-[#15171b] text-white lg:h-auto lg:flex-1">
					<div className="relative min-h-0 flex-1">
						<div ref={areaRef} className="absolute inset-3 grid place-items-center sm:inset-6">
							{!turned && <img src={pickedFile.url} alt="" className="hidden" onLoad={(loadEvent) => setNaturalSize({ width: loadEvent.target.naturalWidth, height: loadEvent.target.naturalHeight })} />}
							{!turned && <p className="text-sm text-white/60">Loading…</p>}
							{turned && fit > 0 && (
								<div ref={stageRef} className="relative touch-none select-none overflow-hidden shadow-2xl" style={stageStyle}>
									<img
										src={pickedFile.url}
										alt=""
										draggable={false}
										className="pointer-events-none absolute left-1/2 top-1/2 max-w-none"
										style={{
											width: rotate % 180 === 0 ? '100%' : `${(rotated.height / rotated.width) * 100}%`,
											height: rotate % 180 === 0 ? '100%' : `${(rotated.width / rotated.height) * 100}%`,
											filter: adjustFilter(adjust),
											// the box shows the biggest empty-corner-free part, so the picture is drawn larger than the box
											transform: `translate(-50%, -50%) rotate(${straighten}deg) scale(${1 / straightenScale(rotated.width, rotated.height, straighten)}) rotate(${rotate}deg) scaleX(${flip ? -1 : 1})`,
										}}
									/>
									<div
										className="absolute cursor-move border border-white shadow-[0_0_0_9999px_rgba(0,0,0,0.6)]"
										style={{ left: `${crop.x * 100}%`, top: `${crop.y * 100}%`, width: `${crop.width * 100}%`, height: `${crop.height * 100}%` }}
										onPointerDown={(pointerEvent) => startDrag(pointerEvent, 'move')}
										onPointerMove={moveDrag}
										onPointerUp={endDrag}
										onPointerCancel={endDrag}
									>
										<div className="pointer-events-none absolute inset-0">
											<span className="absolute inset-y-0 left-1/3 w-px bg-white/35" />
											<span className="absolute inset-y-0 left-2/3 w-px bg-white/35" />
											<span className="absolute inset-x-0 top-1/3 h-px bg-white/35" />
											<span className="absolute inset-x-0 top-2/3 h-px bg-white/35" />
										</div>
										{visibleHandles.map((name) => (
											<span
												key={name}
												className="absolute grid size-7 -translate-x-1/2 -translate-y-1/2 place-items-center"
												style={{ left: HANDLES[name][0], top: HANDLES[name][1], cursor: CURSORS[name] }}
												onPointerDown={(pointerEvent) => startDrag(pointerEvent, name)}
												onPointerMove={moveDrag}
												onPointerUp={endDrag}
												onPointerCancel={endDrag}
											>
												<span className="size-3 rounded-sm border border-black/40 bg-white" />
											</span>
										))}
									</div>
								</div>
							)}
						</div>
					</div>
					<div className="tnum flex items-center justify-between gap-3 border-t border-white/10 px-5 py-3 text-xs text-white/70">
						<span>{turned ? `${cropWidthPixels} × ${cropHeightPixels} px · ${shapeText}` : ' '}</span>
						{naturalSize && <span>Original {naturalSize.width} × {naturalSize.height}</span>}
					</div>
				</div>

				{/* the tools */}
				<aside className="flex min-h-0 w-full flex-1 flex-col lg:w-[22rem] lg:flex-none lg:shrink-0 lg:border-l lg:border-line">
					<div className="flex items-start justify-between gap-3 px-5 pb-3 pt-4 sm:pt-5">
						<div className="min-w-0">
							<h2 className="text-lg font-semibold leading-tight">Basic editor</h2>
							<p className="truncate text-sm text-muted" title={pickedFile.file.name}>{pickedFile.file.name}</p>
						</div>
						<button type="button" onClick={onClose} aria-label="Close" className={btn('ghost', 'sm', 'px-2')}><Icon name="x" className="size-5" /></button>
					</div>

					<div role="tablist" aria-label="Editor tools" className="mx-5 grid grid-cols-3 gap-1 rounded-2xl bg-sunken p-1">
						{TABS.map(([id, label]) => (
							<button
								key={id}
								type="button"
								role="tab"
								aria-selected={tab === id}
								onClick={() => setTab(id)}
								className={`relative rounded-xl py-2 text-sm font-medium transition ${tab === id ? 'bg-surface shadow-sm' : 'text-muted hover:text-ink'}`}
							>
								{label}
								{changed[id] && <span className="absolute right-2.5 top-2 size-1.5 rounded-full bg-accent" aria-label="changed" />}
							</button>
						))}
					</div>

					<div className="min-h-0 flex-1 overflow-y-auto px-5 py-4 sm:py-5">
						{tab === 'crop' && (
							<div className="space-y-4">
								<div role="group" aria-label="Crop shape" className="space-y-2">
									<button
										type="button"
										onClick={() => choosePreset('free')}
										disabled={!turned}
										aria-pressed={presetId === 'free'}
										className={`flex w-full items-center gap-3 rounded-2xl px-4 py-3 text-left transition disabled:opacity-50 ${presetId === 'free' ? 'bg-accent/12 text-accent ring-2 ring-accent' : 'ring-1 ring-line hover:bg-sunken'}`}
									>
										<ShapeGlyph width={4} height={3} dashed />
										<span>
											<span className="block text-sm font-semibold leading-tight">Free roam</span>
											<span className="block text-xs text-muted">Any shape, drag the handles</span>
										</span>
									</button>
									<div className="grid grid-cols-3 gap-2">
										{RATIO_PRESETS.map((preset) => {
											const original = preset.ratio === 'original'
											return (
												<ShapeTile
													key={preset.id}
													title={original ? 'Original' : `${preset.width}:${preset.height}`}
													subtitle={original ? 'Same shape' : platformName(preset.width, preset.height)}
													glyph={<ShapeGlyph width={original ? (turned?.width || 4) : preset.width} height={original ? (turned?.height || 3) : preset.height} />}
													selected={presetId === preset.id}
													disabled={!turned}
													onClick={() => choosePreset(preset.id)}
												/>
											)
										})}
									</div>
								</div>
								<button type="button" onClick={swapShape} disabled={!ratio || ratio.width === ratio.height} className={btn('secondary', 'sm', 'w-full')}>Swap portrait and landscape</button>
								<p className="text-xs text-muted">Drag the box to move it and the handles to resize it. Pick a shape to lock the box to that ratio.</p>
							</div>
						)}

						{tab === 'rotate' && (
							<div className="space-y-6">
								<div className="grid grid-cols-2 gap-2">
									<ActionButton icon="rotateLeft" label="Rotate left" onClick={() => rotateBy(-1)} disabled={!turned} />
									<ActionButton icon="rotateRight" label="Rotate right" onClick={() => rotateBy(1)} disabled={!turned} />
									<ActionButton icon="flipH" label="Flip horizontally" onClick={() => flipView(false)} disabled={!turned} />
									<ActionButton icon="flipV" label="Flip vertically" onClick={() => flipView(true)} disabled={!turned} />
								</div>
								<Slider id="straighten-angle" label="Straighten" value={straighten} min={-MAX_STRAIGHTEN} max={MAX_STRAIGHTEN} step={0.1} disabled={!turned}
									format={(value) => `${value.toFixed(1)}°`} onChange={setStraighten} />
								<p className="text-xs text-muted">Straighten turns the picture a little and trims the empty corners. Double-click a slider to set it back to zero.</p>
							</div>
						)}

						{tab === 'colour' && (
							<div className="space-y-6">
								<Slider id="adjust-brightness" label="Brightness" value={adjust.brightness} min={-100} max={100} step={1} disabled={!turned} onChange={(value) => setAdjust({ ...adjust, brightness: value })} />
								<Slider id="adjust-contrast" label="Contrast" value={adjust.contrast} min={-100} max={100} step={1} disabled={!turned} onChange={(value) => setAdjust({ ...adjust, contrast: value })} />
								<Slider id="adjust-saturation" label="Saturation" value={adjust.saturation} min={-100} max={100} step={1} disabled={!turned} onChange={(value) => setAdjust({ ...adjust, saturation: value })} />
								<button type="button" onClick={() => setAdjust(NO_ADJUST)} disabled={!hasAdjust(adjust)} className={btn('secondary', 'sm', 'w-full')}>Reset colour</button>
							</div>
						)}
					</div>

					<div className="shrink-0 space-y-3 border-t border-line px-5 py-3 sm:py-4">
						{note && <p className="text-xs text-muted">{note}</p>}
						<div className="flex flex-wrap items-center justify-between gap-x-2 gap-y-2">
							<button type="button" className={btn('ghost', 'sm')} onClick={reset} disabled={!turned}>Reset all</button>
							<div className="ml-auto flex items-center gap-2">
								<button type="button" className={btn('secondary', 'md')} onClick={onClose}>Cancel</button>
								<button type="button" className={btn('primary', 'md')} disabled={!turned} onClick={() => onApply(toEdit({ rotate, flip, straighten, adjust, crop }))}>{applyLabel}</button>
							</div>
						</div>
					</div>
				</aside>
			</div>
		</Modal>
	)
}
