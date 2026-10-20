import { useState } from 'react'
import { api } from '../../api/client.js'
import { fmtBytes, fmtDate, plural } from '../../lib/format.js'
import { jobTitle } from '../cards/JobCard.jsx'
import Icon from '../icons/Icon.jsx'
import { btn } from '../ui/buttonStyles.js'
import { Modal } from '../ui/Modal.jsx'
import { useToast } from '../ui/Toast.jsx'

// "Remove at your own risk" confirmation shown before any job is deleted
export default function DeleteDialog({ job, onClose, onDeleted }) {
	const [sure, setSure] = useState(false)
	const [busy, setBusy] = useState(false)
	const [error, setError] = useState('')
	const toast = useToast()

	if (!job) return null

	const folder = job.path.replace(/[\\/]out$/, '')

	const confirm = async () => {
		setBusy(true)
		setError('')
		try {
			await api.remove(job.id)
			toast('Job deleted')
			onDeleted()
		} 
		catch (error) { 
			setError(error.message)
			setBusy(false) 
		}
	}

	return (
		<Modal 
			open 
			onClose={busy ? undefined : onClose} 
			label="Delete job" 
			closable={!busy}
		>
			<div className="flex items-start gap-4">
				<span className="grid size-12 shrink-0 place-items-center rounded-2xl bg-bad/15 text-bad">
					<Icon name="trash" className="size-6" />
				</span>
				<div className="min-w-0">
					<h2 className="text-xl font-semibold">Delete this job permanently?</h2>
					<p className="mt-1 text-sm text-muted">{jobTitle(job)} · {fmtDate(job.created)}</p>
				</div>
			</div>

			<div className="mt-6 space-y-4 text-[15px] leading-relaxed">
				<p>Everything related to this job will be deleted from your disk as well:</p>
				<ul className="list-disc space-y-1 pl-5 text-muted marker:text-bad">
					<li><span className="text-ink">{plural(job.done, 'result file')}</span> ({fmtBytes(job.total_bytes)})</li>
					<li>the preview images and the job record, so it disappears from History</li>
				</ul>
				<div>
					<p className="mb-1.5 text-xs font-medium uppercase tracking-wide text-muted">Stored at</p>
					<code className="block break-all rounded-xl bg-sunken px-3.5 py-3 font-mono text-xs leading-relaxed">{folder}</code>
				</div>
				<p className="rounded-xl bg-bad/10 p-3.5 text-sm text-bad">
					This can't be undone. Remove it at your own risk. If you still need these files, download them first.
					Your original files are not affected.
				</p>
				<label className="flex cursor-pointer items-center gap-3 text-sm font-medium">
					<input 
						type="checkbox" 
						checked={sure} 
						onChange={(event) => setSure(event.target.checked)} 
						className="size-5 accent-[var(--bad)]" 
					/>

					I understand, delete everything related to this job
				</label>
				{error && <p className="text-sm text-bad" role="alert">{error}</p>}
			</div>

			<div className="mt-7 flex flex-col-reverse gap-2.5 sm:flex-row sm:justify-end">
				{job.done > 0 && 
					<a href={api.zipUrl(job.id)} className={btn('ghost', 'md', 'sm:mr-auto')}>
						<Icon name="download" className="size-4" />Download .zip first
					</a>
				}
				<button 
					type="button" 
					className={btn('secondary')} 
					onClick={onClose} 
					disabled={busy}
				>
					Keep it
				</button>

				<button 
					type="button" 
					className={btn('danger')} 
					onClick={confirm} 
					disabled={!sure || busy}
				>
					{busy ? 'Deleting…' : 'Delete permanently'}
				</button>
			</div>
		</Modal>
	)
}
