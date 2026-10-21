import { useCallback, useEffect, useRef, useState } from 'react'
import { CropEditor } from '../features/editor/CropEditor.jsx'
import { editedSize } from '../features/editor/editMath.js'
import { PickedCard } from '../components/cards/PickedCard.jsx'
import Icon from '../components/icons/Icon.jsx'
import { btn } from '../components/ui/buttonStyles.js'
import { toPayload } from '../features/settings/defaults.js'
import Settings from '../features/settings/Settings.jsx'
import { plural } from '../lib/format.js'
import { IMG_EXT, VID_EXT, kindOf, readMediaSize } from '../lib/media.js'
import { modelLabel, modelProblem } from '../lib/models.js'

let uid = 0

export default function NewJobPage({ 
	opts, 
	setOpts, 
	models, 
	modelsDir, 
	onRefreshModels, 
	refreshing, 
	system, 
	onStart 
}) {
	const [files, setFiles] = useState([])
	const [notice, setNotice] = useState('')
	const [over, setOver] = useState(false)
	const [edits, setEdits] = useState({})            // crop and rotate per picked file id
	const [editingId, setEditingId] = useState(null)
	const input = useRef(null)
	const filesRef = useRef(files)
	filesRef.current = files

	const lock = files[0]?.kind || null     // a job is all images or all videos, never both

	// the watermark preview copies the proportions of the first picked file
	const [firstFileSize, setFirstFileSize] = useState(null)
	const firstFile = files[0]
	useEffect(() => {
		if (!firstFile) { setFirstFileSize(null); return }
		let cancelled = false
		readMediaSize(firstFile.url, firstFile.kind)
			.then((size) => { if (!cancelled) setFirstFileSize(size) })
			.catch(() => { if (!cancelled) setFirstFileSize(null) })
		return () => { cancelled = true }
	}, [firstFile?.id, firstFile?.url, firstFile?.kind])

	const add = useCallback((list) => {
		let kind = filesRef.current[0]?.kind || null
		const picked = []
		let unsupported = 0, mixed = 0
		for (const file of [...list]) {
			const fileKind = kindOf(file.name)
			if (!fileKind) { 
				unsupported++
				continue 
			}
			
			kind = kind || fileKind
			if (fileKind !== kind) { 
				mixed++
				continue 
			}
			picked.push({ id: ++uid, file, kind: fileKind, url: URL.createObjectURL(file) })
		}
		const msgs = []
		if (mixed) msgs.push(`${plural(mixed, 'file')} skipped: images and videos can't be processed in the same job. Clear the list to switch type.`)
		if (unsupported) msgs.push(`${plural(unsupported, 'file')} skipped: unsupported format.`)
		setNotice(msgs.join(' '))
		if (picked.length) setFiles((cur) => [...cur, ...picked])
	}, [])

	// removing a file
	const remove = (id) => {
		setEdits((cur) => { const { [id]: dropped, ...rest } = cur; return rest })
		removeFile(id)
	}
	const removeFile = (id) => setFiles((cur) => {
		cur.filter((pickedFile) => pickedFile.id === id).forEach((pickedFile) => URL.revokeObjectURL(pickedFile.url))
		return cur.filter((pickedFile) => pickedFile.id !== id)
	})

	// clear everything
	const clear = () => { 
		files.forEach((pickedFile) => URL.revokeObjectURL(pickedFile.url))
		setFiles([]) 
		setEdits({})
		setNotice('') 
	}
	useEffect(() => () => filesRef.current.forEach((pickedFile) => URL.revokeObjectURL(pickedFile.url)), [])

	// paste an image from the clipboard
	useEffect(() => {
		const handlePaste = (pasteEvent) => { const pastedFiles = [...(pasteEvent.clipboardData?.files || [])]; if (pastedFiles.length) add(pastedFiles) }
		window.addEventListener('paste', handlePaste)
		return () => window.removeEventListener('paste', handlePaste)
	}, [add])

	const problem = modelProblem(opts, models)
	const wmMissing = opts.wm_on && !opts.wm.text.trim()
	const noFfmpeg = lock === 'video' && system && !system.ffmpeg
	const noTorch = opts.scale > 1 && system?.backend === 'none'
	const blocker = problem || (wmMissing && 'Enter the watermark text, or turn the watermark off.') ||
		(noFfmpeg && "FFmpeg wasn't found, so videos can't be processed. Run python setup.py.") ||
		(noTorch && 'PyTorch is not installed. Run python setup.py, or set Upscale to Off.') || ''

	const start = async () => {
		const started = await onStart(files, toPayload(opts), files.map((pickedFile) => edits[pickedFile.id] || null))
		if (started) clear()
	}

	const accept = lock === 'image' ? 'image/*' : lock === 'video' ? 'video/*,.mkv' : 'image/*,video/*,.mkv'
	const summary = [
		files.length ? plural(files.length, lock) : 'No files yet',
		opts.scale > 1 ? `${modelLabel(opts, models)} · ${opts.scale}×` : 'No upscaling',
		lock === 'video' ? 'MP4' : opts.fmt.toUpperCase(),
		opts.wm_on && opts.wm.text.trim() ? 'watermark' : null,
	].filter(Boolean).join('  ·  ')

	return (
		<>
			<div className="mb-8">
				<h1 className="text-3xl font-semibold tracking-tight">New job</h1>
				<p className="mt-2 max-w-2xl text-muted">Add images or videos, choose how to upscale them, and optionally stamp a watermark. Everything stays on this computer.</p>
			</div>

			<div className="grid items-start gap-8 lg:grid-cols-[minmax(0,1fr)_420px] xl:grid-cols-[minmax(0,1fr)_460px] xl:gap-10">
				<div className="min-w-0 space-y-6">

					{/* file input */}
					<div
						role="button" tabIndex={0} aria-label="Add files"
						onClick={() => input.current.click()}
						onKeyDown={(event) => (event.key === 'Enter' || event.key === ' ') && (event.preventDefault(), input.current.click())}
						onDragOver={(event) => { event.preventDefault(); setOver(true) }}
						onDragLeave={() => setOver(false)}
						onDrop={(event) => { event.preventDefault(); setOver(false); add(event.dataTransfer.files) }}
						className={`flex cursor-pointer flex-col items-center justify-center gap-3 rounded-3xl border-2 border-dashed text-center transition ${over ? 'border-accent bg-accent/10' : 'border-line bg-surface/60 hover:border-accent/60 hover:bg-surface'} ${files.length ? 'px-6 py-8' : 'px-6 py-20'}`}>
						<input 
							ref={input} 
							type="file" 
							hidden 
							multiple 
							accept={accept} 
							onChange={(event) => { add(event.target.files); event.target.value = '' }} 
						/>
						<span className={`grid place-items-center rounded-2xl bg-accent/15 text-accent ${files.length ? 'size-12' : 'size-16'}`}><Icon name="upload" className={files.length ? 'size-6' : 'size-8'} /></span>
						<div>
							<p className={`font-semibold ${files.length ? 'text-base' : 'text-xl'}`}>{files.length ? `Add more ${lock}s` : 'Drop images or videos here'}</p>
							<p className="mt-1 text-sm text-muted">or click to browse{!files.length && ' · paste works too'}</p>
						</div>
						{!files.length && (
							<p className="mt-1 text-xs text-muted">
								{IMG_EXT.map((event) => event.slice(1)).join(', ')} · {VID_EXT.map((event) => event.slice(1)).join(', ')}
							</p>
						)}
					</div>

					{notice && (
						<p role="alert" className="flex gap-3 rounded-2xl bg-warn/12 p-4 text-sm text-warn ring-1 ring-warn/30">
							<Icon name="alert" className="mt-0.5 size-4 shrink-0" />{notice}
						</p>
					)}

					{files.length > 0 && (
						<ul className="grid grid-cols-2 gap-5 sm:grid-cols-3 xl:grid-cols-4">
							{files.map((pickedFile) => <li key={pickedFile.id} className="min-w-0"><PickedCard pickedFile={pickedFile} edited={Boolean(edits[pickedFile.id])} onEdit={() => setEditingId(pickedFile.id)} onRemove={() => remove(pickedFile.id)} /></li>)}
						</ul>
					)}
				</div>

				<aside className="min-w-0">
					<Settings 
						opts={opts} 
						setOpts={setOpts} 
						models={models} 
						modelsDir={modelsDir} 
						onRefreshModels={onRefreshModels} 
						refreshing={refreshing} 
						sourceSize={firstFileSize && editedSize(firstFileSize.width, firstFileSize.height, edits[firstFile?.id])}
					/>
				</aside>
			</div>

			<div className="sticky bottom-4 z-30 mt-10">
				<div className="flex flex-col gap-4 rounded-2xl bg-surface/95 p-4 ring-1 ring-line shadow-2xl backdrop-blur sm:flex-row sm:items-center sm:justify-between sm:px-6">
					<div className="min-w-0">
						<p className="tnum truncate text-[15px] font-medium">{summary}</p>
						{blocker && files.length > 0 && <p className="mt-0.5 text-sm text-bad">{blocker}</p>}
					</div>
					<div className="flex shrink-0 gap-2.5">
						{files.length > 0 && <button type="button" className={btn('ghost')} onClick={clear}>Clear all</button>}
						<button 
							type="button" 
							className={btn('primary', 'lg')} 
							disabled={!files.length || !!blocker} 
							onClick={start}
						>
							<Icon name="sparkles" className="size-5" />{files.length ? `Process ${plural(files.length, lock)}` : 'Add files to start'}
						</button>
					</div>
				</div>
			</div>
			{editingId && (
				<CropEditor
					pickedFile={files.find((pickedFile) => pickedFile.id === editingId)}
					edit={edits[editingId]}
					onClose={() => setEditingId(null)}
					onApply={(edit) => {
						setEdits((cur) => { const next = { ...cur }; if (edit) next[editingId] = edit; else delete next[editingId]; return next })
						setEditingId(null)
					}}
				/>
			)}
		</>
	)
}
