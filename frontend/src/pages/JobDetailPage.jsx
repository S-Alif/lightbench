import { useCallback, useEffect, useState } from 'react'
import { api } from '../api/client.js'
import { jobTitle } from '../components/cards/JobCard.jsx'
import { ResultCard } from '../components/cards/ResultCard.jsx'
import Icon from '../components/icons/Icon.jsx'
import DeleteDialog from '../components/jobs/DeleteDialog.jsx'
import { Badge, StatusBadge } from '../components/ui/Badge.jsx'
import { btn } from '../components/ui/buttonStyles.js'
import { Modal } from '../components/ui/Modal.jsx'
import { useToast } from '../components/ui/Toast.jsx'
import { navigateTo } from '../hooks/useRoute.js'
import { copyText } from '../lib/clipboard.js'
import { fmtBytes, fmtClock, fmtDate } from '../lib/format.js'
import { modelLabel } from '../lib/models.js'

function Viewer({ job, items, index, onIndex, onClose }) {
	const item = items[index]

	useEffect(() => {

		const key = (event) => {
			if (event.key === 'ArrowLeft') onIndex((index - 1 + items.length) % items.length)
			if (event.key === 'ArrowRight') onIndex((index + 1) % items.length)
		}

		document.addEventListener('keydown', key)
		return () => document.removeEventListener('keydown', key)

	}, [index, items.length, onIndex])
	if (!item) return null

	// this part is ai, I was just lazy
	return (
		<Modal 
			open 
			onClose={onClose} 
			label={item.out_name} 
			size="xl"
		>
			<div className="mb-5 flex items-center gap-3">
				<div className="min-w-0 flex-1">
					<p className="truncate text-lg font-semibold">{item.out_name}</p>
					<p className="tnum text-sm text-muted">{item.w ? `${item.w}×${item.h} · ` : ''}{fmtBytes(item.size)}{items.length > 1 ? ` · ${index + 1} of ${items.length}` : ''}</p>
				</div>

				{/* download button */}
				<a 
					href={api.fileUrl(job.id, item.id)} 
					className={btn('primary', 'sm')}
				>
					<Icon name="download" className="size-4" />
					Download
				</a>

				<button 
					type="button" 
					onClick={onClose} 
					aria-label="Close" 
					className={btn('ghost', 'sm', 'px-2.5')}
				>
					<Icon name="x" className="size-5" />
				</button>
			</div>
			<div className="relative grid min-h-[40vh] place-items-center overflow-hidden rounded-2xl bg-sunken">
				{item.kind === 'image'
					? <img key={item.id} src={api.fileUrl(job.id, item.id, true)} alt={item.out_name} className="max-h-[72vh] w-auto max-w-full object-contain" />
					: <video key={item.id} src={api.fileUrl(job.id, item.id, true)} controls autoPlay className="max-h-[72vh] max-w-full" />}
				{items.length > 1 && (
					<>
						<button 
							type="button" 
							aria-label="Previous" 
							onClick={() => onIndex((index - 1 + items.length) % items.length)}
							className="absolute left-3 top-1/2 grid size-11 -translate-y-1/2 place-items-center rounded-full bg-black/55 text-white backdrop-blur hover:bg-black/75"
						>
							<Icon name="left" />
						</button>
						<button 
							type="button" 
							aria-label="Next" 
							onClick={() => onIndex((index + 1) % items.length)}
							className="absolute right-3 top-1/2 grid size-11 -translate-y-1/2 place-items-center rounded-full bg-black/55 text-white backdrop-blur hover:bg-black/75"
						>
							<Icon name="right" />
						</button>
					</>
				)}
			</div>
		</Modal>
	)
}

// main function
export default function JobDetailPage({ id, system, models }) {
	const [job, setJob] = useState(null)
	const [error, setError] = useState('')
	const [view, setView] = useState(null)
	const [del, setDel] = useState(false)
	const toast = useToast()

	const load = useCallback(() => api.job(id).then(setJob).catch((loadError) => setError(loadError.message)), [id])

	useEffect(() => { 
		setJob(null)
		setError('')
		load() 
	}, [load])

	const active = job && (job.status === 'running' || job.status === 'queued')

	useEffect(() => { if (!active) return; const intervalId = setInterval(load, 1500); return () => clearInterval(intervalId) }, [active, load])

	if (error) {
		return (
			<div className="grid place-items-center rounded-3xl border-2 border-dashed border-line px-6 py-24 text-center">
				<p className="text-xl font-semibold">This job isn't here any more</p>
				<p className="mt-1 text-muted">It may have been deleted.</p>
				<button type="button" className={btn('primary', 'md', 'mt-6')} onClick={() => navigateTo('history')}>Back to history</button>
			</div>
		)
	}
	if (!job) return <p className="text-muted">Loading…</p>

	const jobOptions = job.options || {}
	const folder = job.path.replace(/[\\/]out$/, '')
	const done = job.items.filter((item) => item.status === 'done')
	const failed = job.items.filter((item) => item.status !== 'done')
	const chips = [
		jobOptions.scale > 1 ? `${modelLabel(jobOptions, models)} · ${jobOptions.scale}×` : 'No upscaling',
		job.kind === 'video' ? 'MP4' : (jobOptions.fmt || '').toUpperCase(),
		jobOptions.watermark?.text ? `Watermark “${jobOptions.watermark.text}”` : null,
		jobOptions.keep_metadata ? 'Metadata kept' : 'Metadata stripped',
	].filter(Boolean)

	return (
		<>
			<button 
				type="button" 
				onClick={() => navigateTo('history')} 
				className="mb-6 inline-flex items-center gap-1.5 text-sm font-medium text-muted hover:text-ink"
			>
				<Icon name="left" className="size-4" />History
			</button>

			<div className="mb-8 flex flex-wrap items-start justify-between gap-6">
				<div className="min-w-0">
					<div className="flex flex-wrap items-center gap-3">
						<h1 className="text-3xl font-semibold tracking-tight first-letter:uppercase">{jobTitle(job)}</h1>
						<StatusBadge status={job.status} />
					</div>
					<p className="tnum mt-2 text-muted">
						{fmtDate(job.created)}{job.elapsed >= 1 ? ` · took ${fmtClock(job.elapsed)}` : ''} · {fmtBytes(job.total_bytes)}
					</p>
					<div className="mt-4 flex flex-wrap gap-2">{chips.map((chip) => <Badge key={chip}>{chip}</Badge>)}</div>
				</div>
				<div className="flex flex-wrap gap-2.5">
					{done.length > 0 && <a href={api.zipUrl(job.id)} className={btn('primary')}><Icon name="download" className="size-5" />Download all ({done.length})</a>}
					<button 
						type="button" 
						className={btn('dangerSoft')} 
						disabled={active} 
						onClick={() => setDel(true)}
					>
						<Icon name="trash" className="size-5" />Delete job
					</button>
				</div>
			</div>

			<div className="mb-10 flex flex-wrap items-center gap-x-4 gap-y-3 rounded-2xl bg-surface p-4 ring-1 ring-line sm:px-5">
				<Icon name="folder" className="size-5 shrink-0 text-accent" />
				<div className="min-w-0 flex-1 basis-64">
					<p className="text-xs font-medium uppercase tracking-wide text-muted">Files are stored at</p>
					<code className="block break-all font-mono text-xs leading-relaxed sm:text-[13px]">{job.path}</code>
				</div>
				<div className="flex gap-2">
					<button 
						type="button" 
						className={btn('secondary', 'sm')} 
						onClick={async () => toast((await copyText(job.path)) ? 'Path copied' : 'Could not copy')}
					>
						<Icon name="copy" className="size-4" />Copy path
					</button>
					{system?.local && (
						<button 
							type="button" 
							className={btn('secondary', 'sm')} 
							onClick={() => api.openFolder(job.id).catch((openError) => toast(openError.message, 'bad'))}
						>
							<Icon name="folder" className="size-4" />Open folder
						</button>
					)}
				</div>
			</div>

			{job.items.length > 0 && (
				<ul className="grid grid-cols-2 gap-5 sm:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5">
					{job.items.map((item) => {
						const doneIndex = done.findIndex((doneItem) => doneItem.id === item.id)
						return <li key={item.id} className="min-w-0"><ResultCard jobId={job.id} item={item} onOpen={() => setView(doneIndex)} /></li>
					})}
				</ul>
			)}
			{failed.length > 0 && done.length === 0 && !active && (
				<p className="mt-6 text-sm text-muted">Nothing was produced. The error for each file is shown on its card.</p>
			)}

			{view !== null && done[view] && <Viewer job={job} items={done} index={view} onIndex={setView} onClose={() => setView(null)} />}
			{del && <DeleteDialog job={{ ...job, folder }} onClose={() => setDel(false)} onDeleted={() => navigateTo('history')} />}
		</>
	)
}
