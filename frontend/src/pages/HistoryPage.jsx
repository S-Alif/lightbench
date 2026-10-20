import { useCallback, useEffect, useState } from 'react'
import { api } from '../api/client.js'
import { JobCard } from '../components/cards/JobCard.jsx'
import Icon from '../components/icons/Icon.jsx'
import DeleteDialog from '../components/jobs/DeleteDialog.jsx'
import { btn } from '../components/ui/buttonStyles.js'
import { useToast } from '../components/ui/Toast.jsx'
import { navigateTo } from '../hooks/useRoute.js'
import { copyText } from '../lib/clipboard.js'
import { fmtBytes, plural } from '../lib/format.js'

const TABS = [['all', 'All'], ['image', 'Images'], ['video', 'Videos']]

// job history display
export default function HistoryPage({ system }) {
	const [data, setData] = useState(null)
	const [error, setError] = useState('')
	const [tab, setTab] = useState('all')
	const [del, setDel] = useState(null)
	const toast = useToast()

	const load = useCallback(() => api.jobs().then(setData).catch((loadError) => setError(loadError.message)), [])

	useEffect(() => {
		load() 
	}, [load])

	// keep the list fresh while something is still processing
	const anyActive = data?.jobs.some((job) => job.status === 'running' || job.status === 'queued')
	useEffect(() => { 
		if (!anyActive) return
		const intervalId = setInterval(load, 2000)
		return () => clearInterval(intervalId) 
	}, [anyActive, load])

	const jobs = (data?.jobs || []).filter((job) => tab === 'all' || job.kind === tab)
	const totalBytes = (data?.jobs || []).reduce((total, job) => total + job.total_bytes, 0)

	return (
		<>
			<div className="mb-8 flex flex-wrap items-end justify-between gap-4">
				<div>
					<h1 className="text-3xl font-semibold tracking-tight">History</h1>
					<p className="mt-2 text-muted">
						{data ? `${plural(data.jobs.length, 'job')} · ${fmtBytes(totalBytes)} on disk` : 'Loading…'}
					</p>
				</div>
				<div className="flex gap-1 rounded-xl bg-sunken p-1" role="tablist">
					{TABS.map(([tabKey, tabLabel]) => (
						<button key={tabKey} role="tab" aria-selected={tab === tabKey} onClick={() => setTab(tabKey)}
							className={`h-9 rounded-lg px-4 text-sm font-medium transition ${tab === tabKey ? 'bg-surface text-ink shadow-sm ring-1 ring-line' : 'text-muted hover:text-ink'}`}>{tabLabel}</button>
					))}
				</div>
			</div>

			{data && (
				<div className="mb-8 flex flex-wrap items-center gap-x-4 gap-y-2 rounded-2xl bg-surface p-4 ring-1 ring-line">
					<Icon name="folder" className="size-5 shrink-0 text-accent" />
					<p className="text-sm text-muted">All results are stored in</p>
					<code className="min-w-0 flex-1 basis-64 break-all font-mono text-xs">{data.data_dir}</code>
					<button type="button" className={btn('ghost', 'sm')} onClick={async () => toast((await copyText(data.data_dir)) ? 'Path copied' : 'Could not copy', 'ok')}>
						<Icon name="copy" className="size-4" />Copy
					</button>
				</div>
			)}

			{error && <p className="rounded-2xl bg-bad/10 p-4 text-bad" role="alert">{error}</p>}

			{data && jobs.length === 0 && (
				<div className="grid place-items-center rounded-3xl border-2 border-dashed border-line px-6 py-24 text-center">
					<span className="mb-4 grid size-16 place-items-center rounded-2xl bg-sunken text-muted"><Icon name="history" className="size-8" /></span>
					<p className="text-xl font-semibold">{data.jobs.length ? `No ${tab} jobs yet` : 'Nothing here yet'}</p>
					<p className="mt-1 max-w-sm text-muted">Finished jobs show up here so you can come back and download them again.</p>
					<button type="button" className={btn('primary', 'md', 'mt-6')} onClick={() => navigateTo('')}><Icon name="plus" className="size-5" />Start a job</button>
				</div>
			)}

			{jobs.length > 0 && (
				<ul className="grid grid-cols-2 gap-5 sm:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5">
					{jobs.map((job) => (
						<li key={job.id} className="min-w-0">
							<JobCard job={job} onOpen={() => navigateTo(`job/${job.id}`)} onDelete={() => setDel(job)} />
						</li>
					))}
				</ul>
			)}

			{/* delete dialog */}
			<DeleteDialog 
				job={del} 
				onClose={() => setDel(null)} 
				onDeleted={() => { setDel(null); load() }} 
			/>
		</>
	)
}
