// tell the app when the server asks for the password (never logged in, or the session ran out)
export const LOCKED_EVENT = 'lightbench:locked'
const announceLocked = () => window.dispatchEvent(new Event(LOCKED_EVENT))

const json = async (response) => {
	const body = await response.json().catch(() => ({}))
	if (response.status === 401 && body.error === 'Password required') announceLocked()
	if (!response.ok) throw new Error(body.error || body.detail || response.statusText)
	return body
}

export const api = {
	authStatus: () => fetch('/api/auth/status').then(json),
	login: (password) => fetch('/api/auth/login', {
		method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ password }),
	}).then(json),
	logout: () => fetch('/api/auth/logout', { method: 'POST' }).then(json),
	system: () => fetch('/api/system').then(json),
	usage: () => fetch('/api/system/usage').then(json),
	inspect: (file) => {
		const formData = new FormData()
		formData.append('file', file)
		return fetch('/api/inspect', { method: 'POST', body: formData }).then(json)
	},
	itemMetadata: (jobId, itemId) => fetch(`/api/jobs/${jobId}/items/${itemId}/metadata`).then(json),
	models: () => fetch('/api/models').then(json),
	jobs: () => fetch('/api/jobs').then(json),
	job: (id) => fetch(`/api/jobs/${id}`).then(json),
	editResult: (jobId, itemId, edit) => fetch(`/api/jobs/${jobId}/items/${itemId}/edit`, {
		method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ edit }),
	}).then(json),
	cancel: (id) => fetch(`/api/jobs/${id}/cancel`, { method: 'POST' }).then(json),
	remove: (id) => fetch(`/api/jobs/${id}`, { method: 'DELETE' }).then(json),
	openFolder: (id) => fetch(`/api/jobs/${id}/open-folder`, { method: 'POST' }).then(json),
	fileUrl: (jid, iid, inline) => `/api/jobs/${jid}/items/${iid}/file${inline ? '?inline=1' : ''}`,
	thumbUrl: (jid, iid) => `/api/jobs/${jid}/items/${iid}/thumb`,
	zipUrl: (jid) => `/api/jobs/${jid}/zip`,

	// XHR instead of fetch so we can show upload progress (big videos, phones over Wi-Fi)
	create(files, options, edits, onProgress) {
		return new Promise((resolve, reject) => {
			const formData = new FormData()
			formData.append('options', JSON.stringify(options))
			if (edits.some(Boolean)) formData.append('edits', JSON.stringify(edits))   // one entry per file, same order
			files.forEach((file) => formData.append('files', file))
			const xhr = new XMLHttpRequest()
			xhr.open('POST', '/api/jobs')
			xhr.upload.onprogress = (progressEvent) => progressEvent.lengthComputable && onProgress?.(progressEvent.loaded / progressEvent.total)
			xhr.onload = () => {
				let body = {}
				try { body = JSON.parse(xhr.responseText) } catch { /* ignore */ }
				if (xhr.status === 401) announceLocked()
				xhr.status < 300 ? resolve(body) : reject(new Error(body.error || `Upload failed (${xhr.status})`))
			}
			xhr.onerror = () => reject(new Error('Could not reach the server'))
			xhr.send(formData)
		})
	},
}
