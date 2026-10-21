const json = async (response) => {
	const body = await response.json().catch(() => ({}))
	if (!response.ok) throw new Error(body.error || body.detail || response.statusText)
	return body
}

export const api = {
	system: () => fetch('/api/system').then(json),
	models: () => fetch('/api/models').then(json),
	jobs: () => fetch('/api/jobs').then(json),
	job: (id) => fetch(`/api/jobs/${id}`).then(json),
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
				xhr.status < 300 ? resolve(body) : reject(new Error(body.error || `Upload failed (${xhr.status})`))
			}
			xhr.onerror = () => reject(new Error('Could not reach the server'))
			xhr.send(formData)
		})
	},
}
