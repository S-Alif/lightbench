import { useMemo, useRef, useState } from 'react'
import Icon from '../../components/icons/Icon.jsx'
import { btn } from '../../components/ui/buttonStyles.js'
import { Modal } from '../../components/ui/Modal.jsx'
import { RATIO_PRESETS, platformName, ratioLabel } from './cropPresets.js'
import { FULL_CROP, fitRatio, moveCrop, resizeCrop, rotatedSize, toEdit, turn } from './editMath.js'

// where each resize handle sits on the crop box, as percentages
const HANDLES = {
	nw: ['0%', '0%'], n: ['50%', '0%'], ne: ['100%', '0%'],
	w: ['0%', '50%'], e: ['100%', '50%'],
	sw: ['0%', '100%'], s: ['50%', '100%'], se: ['100%', '100%'],
}
const CURSORS = { nw: 'nwse-resize', se: 'nwse-resize', ne: 'nesw-resize', sw: 'nesw-resize', n: 'ns-resize', s: 'ns-resize', e: 'ew-resize', w: 'ew-resize' }

// the basic editor: rotate and crop one image
export function CropEditor({ pickedFile, edit, onApply, onClose, applyLabel = 'Apply', note = '' }) {
	const [naturalSize, setNaturalSize] = useState(null)
	const [rotate, setRotate] = useState(edit?.rotate || 0)
	const [crop, setCrop] = useState(edit?.crop || FULL_CROP)
	const [presetId, setPresetId] = useState('free')      // 'free' is free roam
	const [swapped, setSwapped] = useState(false)
	const stageRef = useRef(null)
	const drag = useRef(null)

	const turned = naturalSize ? rotatedSize(naturalSize.width, naturalSize.height, rotate) : null

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
		const nextTurned = rotatedSize(naturalSize.width, naturalSize.height, nextRotate)
		setRotate(nextRotate)
		// a crop made before turning no longer lines up, so start it again
		if (presetId === 'free') { setCrop(FULL_CROP); return }
		const preset = RATIO_PRESETS.find((candidate) => candidate.id === presetId)
		const base = preset.ratio === 'original' ? nextTurned : preset
		refit(swapped ? { width: base.height, height: base.width } : { width: base.width, height: base.height }, nextTurned)
	}

	const reset = () => { setRotate(0); setCrop(FULL_CROP); setPresetId('free'); setSwapped(false) }

	// dragging
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

	return (
		<Modal open onClose={onClose} label="Edit image" size="xl">
			<div className="p-5 sm:p-6">
				<div className="mb-4 flex flex-wrap items-center justify-between gap-3">
					<div className="min-w-0">
						<h2 className="text-lg font-semibold">Crop and rotate</h2>
						<p className="truncate text-sm text-muted" title={pickedFile.file.name}>{pickedFile.file.name}</p>
					</div>
					<div className="flex items-center gap-2">
						<button type="button" className={btn('secondary', 'sm')} onClick={() => rotateBy(-1)} disabled={!turned} aria-label="Rotate left"><Icon name="rotateLeft" className="size-4" />Left</button>
						<button type="button" className={btn('secondary', 'sm')} onClick={() => rotateBy(1)} disabled={!turned} aria-label="Rotate right"><Icon name="rotateRight" className="size-4" />Right</button>
					</div>
				</div>

				<div className="flex justify-center rounded-xl bg-sunken p-3">
					{!turned && <img src={pickedFile.url} alt="" className="hidden" onLoad={(loadEvent) => setNaturalSize({ width: loadEvent.target.naturalWidth, height: loadEvent.target.naturalHeight })} />}
					{!turned && <p className="py-24 text-sm text-muted">Loading…</p>}
					{turned && (
						<div
							ref={stageRef}
							className="relative touch-none select-none overflow-hidden"
							style={{ aspectRatio: `${turned.width} / ${turned.height}`, width: `min(100%, calc(60vh * ${turned.width / turned.height}))` }}
						>
							<img
								src={pickedFile.url}
								alt=""
								draggable={false}
								className="pointer-events-none absolute left-1/2 top-1/2 max-w-none"
								style={{
									width: rotate % 180 === 0 ? '100%' : `${(turned.height / turned.width) * 100}%`,
									height: rotate % 180 === 0 ? '100%' : `${(turned.width / turned.height) * 100}%`,
									transform: `translate(-50%, -50%) rotate(${rotate}deg)`,
								}}
							/>
							<div
								className="absolute cursor-move border border-white shadow-[0_0_0_9999px_rgba(0,0,0,0.55)]"
								style={{ left: `${crop.x * 100}%`, top: `${crop.y * 100}%`, width: `${crop.width * 100}%`, height: `${crop.height * 100}%` }}
								onPointerDown={(pointerEvent) => startDrag(pointerEvent, 'move')}
								onPointerMove={moveDrag}
								onPointerUp={endDrag}
								onPointerCancel={endDrag}
							>
								<div className="pointer-events-none absolute inset-0">
									<span className="absolute inset-y-0 left-1/3 w-px bg-white/40" />
									<span className="absolute inset-y-0 left-2/3 w-px bg-white/40" />
									<span className="absolute inset-x-0 top-1/3 h-px bg-white/40" />
									<span className="absolute inset-x-0 top-2/3 h-px bg-white/40" />
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

				<div className="mt-4 flex flex-wrap items-center gap-2" role="group" aria-label="Crop shape">
					<button type="button" onClick={() => choosePreset('free')} disabled={!turned} aria-pressed={presetId === 'free'} className={btn(presetId === 'free' ? 'primary' : 'secondary', 'sm')}>Free roam</button>
					{RATIO_PRESETS.map((preset) => {
						const label = preset.ratio === 'original' ? 'Original' : `${preset.width}:${preset.height}`
						const name = preset.ratio === 'original' ? '' : platformName(preset.width, preset.height)
						return (
							<button key={preset.id} type="button" onClick={() => choosePreset(preset.id)} disabled={!turned} aria-pressed={presetId === preset.id} className={btn(presetId === preset.id ? 'primary' : 'secondary', 'sm')}>
								{label}{name && <span className="ml-1.5 text-xs opacity-75">{name}</span>}
							</button>
						)
					})}
					{ratio && ratio.width !== ratio.height && <button type="button" onClick={swapShape} className={btn('ghost', 'sm')}>Swap shape</button>}
				</div>

				{note && <p className="mt-4 text-sm text-muted">{note}</p>}

				<div className="mt-5 flex flex-wrap items-center justify-between gap-3">
					<p className="tnum text-sm text-muted">{shapeText}{turned && ` · ${cropWidthPixels}×${cropHeightPixels} px`}</p>
					<div className="flex items-center gap-2">
						<button type="button" className={btn('ghost', 'md')} onClick={reset} disabled={!turned}>Reset</button>
						<button type="button" className={btn('secondary', 'md')} onClick={onClose}>Cancel</button>
						<button type="button" className={btn('primary', 'md')} disabled={!turned} onClick={() => onApply(toEdit(rotate, crop))}>{applyLabel}</button>
					</div>
				</div>
			</div>
		</Modal>
	)
}
