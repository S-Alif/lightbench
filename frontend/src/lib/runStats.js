// ---- numbers shown while a job runs ---------------------------------------------
const FINISHED = ['done', 'error', 'cancelled']

// what state is file number `index` in? (used for the badge and bar on its card)
export function fileState(run, index) {
	if (!run) return null
	if (run.phase === 'uploading') return { kind: 'uploading', progress: run.upload }
	const item = run.job?.items?.[index]
	if (!item) return { kind: 'queued', progress: 0 }
	return { kind: item.status, progress: item.progress || 0, message: item.message, error: item.error }
}

export function summarizeRun(run, nowSeconds) {
	const items = run.job?.items || []
	const total = items.length
	const finished = items.filter((item) => FINISHED.includes(item.status)).length
	const failed = items.filter((item) => item.status === 'error').length
	const succeeded = items.filter((item) => item.status === 'done').length
	const current = items.find((item) => item.status === 'running') || items.find((item) => item.status === 'queued')
	const overall = total ? items.reduce((sum, item) => sum + (FINISHED.includes(item.status) ? 1 : item.progress || 0), 0) / total : 0
	const elapsed = run.job?.elapsed ?? nowSeconds
	const remaining = run.phase === 'processing' && overall > 0.03 ? (elapsed * (1 - overall)) / overall : null
	return { total, finished, failed, succeeded, current, overall, elapsed, remaining }
}
