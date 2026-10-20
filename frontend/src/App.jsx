import { useCallback, useEffect, useState } from 'react'
import { api } from './api/client.js'
import Icon from './components/icons/Icon.jsx'
import Overlay from './components/jobs/Overlay.jsx'
import { Banner } from './components/layout/Banner.jsx'
import { Device } from './components/layout/Device.jsx'
import { btn } from './components/ui/buttonStyles.js'
import { ToastProvider } from './components/ui/Toast.jsx'
import { DEFAULTS } from './features/settings/defaults.js'
import { useStored } from './hooks/usePersistentState.js'
import { navigateTo, useHashRoute } from './hooks/useRoute.js'
import HistoryPage from './pages/HistoryPage.jsx'
import JobDetailPage from './pages/JobDetailPage.jsx'
import NewJobPage from './pages/NewJobPage.jsx'
import GithubBadge from './components/ui/GithubBadge.jsx'

// main app
export default function App() {
	const route = useHashRoute()
	const [theme, setTheme] = useStored('upscaler.theme', 'system')
	const [opts, setOpts] = useStored('upscaler.options.v2', DEFAULTS)
	const [system, setSystem] = useState(null)
	const [models, setModels] = useState([])
	const [modelsDir, setModelsDir] = useState('')
	const [refreshing, setRefreshing] = useState(false)
	const [run, setRun] = useState(null)       // { phase: uploading|processing|done|error, upload, job, error }
	const [jobCount, setJobCount] = useState(null)

	// theme changer
	useEffect(() => {
		const rootElement = document.documentElement
		theme === 'system' ? rootElement.removeAttribute('data-theme') : rootElement.setAttribute('data-theme', theme)
	}, [theme])
	const isDark = theme === 'dark' || (theme === 'system' && matchMedia('(prefers-color-scheme: dark)').matches)

	// refresh models
	const refreshModels = useCallback(async () => {
		setRefreshing(true)
		try { 
			const modelsResponse = await api.models()
			setModels(modelsResponse.models)
			setModelsDir(modelsResponse.dir) 
		} 
		catch { /* server down */ }
		setTimeout(() => setRefreshing(false), 400)
	}, [])

	// check backend and connect
	useEffect(() => {
		api.system().then(setSystem).catch(() => setSystem({ error: 'Cannot reach the server', backend: 'none' }))
		refreshModels()
		// re-attach to a job that is still running (page was reloaded)
		api.jobs().then(async (jobsResponse) => {
			setJobCount(jobsResponse.jobs.length)
			const act = jobsResponse.jobs.find((job) => job.status === 'running' || job.status === 'queued')
			if (act) setRun({ phase: 'processing', upload: 1, job: await api.job(act.id) })
		}).catch(() => { })
	}, [refreshModels])

	useEffect(() => { api.jobs().then((jobsResponse) => setJobCount(jobsResponse.jobs.length)).catch(() => { }) }, [route.page, route.id, run?.phase])

	// poll the running job
	useEffect(() => {
		if (run?.phase !== 'processing') return
		let stop = false, pollTimer
		const id = run.job.id
		const tick = async () => {
			try {
				const latestJob = await api.job(id)
				if (stop) return
				const active = latestJob.status === 'running' || latestJob.status === 'queued'
				setRun((currentRun) => (currentRun ? { ...currentRun, job: latestJob, phase: active ? 'processing' : 'done' } : currentRun))
				if (!active) return
			} catch {
				if (!stop) setRun((currentRun) => (currentRun ? { ...currentRun, phase: 'error', error: 'Lost the connection to the server. Is the app still running?' } : currentRun))
				return
			}
			pollTimer = setTimeout(tick, 600)
		}
		pollTimer = setTimeout(tick, 250)
		return () => { stop = true; clearTimeout(pollTimer) }
	}, [run?.phase, run?.job?.id]) // eslint-disable-line react-hooks/exhaustive-deps

	
	const startRun = async (files, payload) => {
		setRun({ phase: 'uploading', upload: 0 })
		try {
			const job = await api.create(files.map((pickedFile) => pickedFile.file), payload, (uploadFraction) => setRun((currentRun) => (currentRun ? { ...currentRun, upload: uploadFraction } : currentRun)))
			setRun({ phase: 'processing', upload: 1, job })
			return true
		} catch (error) {
			setRun({ phase: 'error', error: error.message })
			return false
		}
	}

	const page = route.page
	const navCls = (active) => `inline-flex h-10 items-center gap-2 whitespace-nowrap rounded-xl px-3 text-sm sm:px-4 font-medium transition ${active ? 'bg-sunken text-ink' : 'text-muted hover:bg-sunken hover:text-ink'}`

	return (
		<ToastProvider>

			{/* header */}
			<header className="sticky top-0 z-40 border-b border-line bg-bg/85 backdrop-blur-md">
				<div className="mx-auto flex h-16 max-w-420 items-center gap-2 px-4 sm:gap-4 sm:px-8">
					<a 
						href="/" 
						className="flex shrink-0 items-center gap-3 text-lg font-semibold tracking-tight sm:mr-2"
						aria-label="Lightbench home" 
					>
						<span className="grid size-9 place-items-center rounded-xl bg-accent text-accent-ink shadow-sm">
							<Icon name="sparkles" className="size-5" />
						</span>
						<span className="hidden sm:inline">Lightbench</span>
					</a>

					{/* navs */}
					<nav className="flex min-w-0 gap-1" aria-label="Main">

						{/* new job link */}
						<a 
							href="/" 
							className={navCls(page === 'new')}
						>
							<Icon name="plus" className="size-4" />New job
						</a>
						{/* history link */}
						<a 
							href="/history" 
							className={navCls(page === 'history' || page === 'job')}
						>
							<Icon name="history" className="size-4" />History
							{jobCount > 0 && <span className="tnum rounded-full bg-accent/15 px-2 text-xs text-accent">{jobCount}</span>}
						</a>
					</nav>
					<div className="ml-auto flex items-center gap-3">
						<Device system={system} />
						<button 
							type="button" 
							onClick={() => setTheme(isDark ? 'light' : 'dark')} 
							aria-label={isDark ? 'Switch to light theme' : 'Switch to dark theme'}
							className={btn('ghost', 'sm', 'px-2.5')}
						>
							<Icon name={isDark ? 'sun' : 'moon'} className="size-5" />
						</button>
					</div>
				</div>
			</header>

			{/* main content */}
			<main className="mx-auto max-w-420 px-4 pb-16 pt-8 sm:px-8 sm:pt-12">
				{system?.error && <Banner>{system.error}</Banner>}
				{system && !system.error && system.backend === 'CPU' && 
					<Banner tone="info">
						No GPU detected, so everything runs on the CPU. It works, just slowly, especially for video.
					</Banner>
				}

				{page === 'history' && <HistoryPage system={system} />}
				{page === 'job' && route.id && <JobDetailPage id={route.id} system={system} models={models} />}
				{(page === 'new' || !['history', 'job'].includes(page)) && (
					<NewJobPage 
						opts={opts} 
						setOpts={setOpts} 
						models={models} 
						modelsDir={modelsDir} 
						onRefreshModels={refreshModels}
						refreshing={refreshing} 
						system={system} 
						onStart={startRun} 
					/>
				)}
			</main>

			{run && (
				<Overlay run={run}
					onCancel={() => run.job && api.cancel(run.job.id)}
					onView={() => { const id = run.job.id; setRun(null); navigateTo(`job/${id}`) }}
					onClose={() => setRun(null)} 
				/>
			)}

			<GithubBadge />
		</ToastProvider>
	)
}
