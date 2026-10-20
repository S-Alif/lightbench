export async function copyText(text) {
	try { await navigator.clipboard.writeText(text); return true } catch { /* not a secure context */ }
	try {
		const textArea = document.createElement('textarea')
		textArea.value = text; textArea.style.position = 'fixed'; textArea.style.opacity = '0'
		document.body.appendChild(textArea); textArea.select()
		const copied = document.execCommand('copy'); textArea.remove(); return copied
	} catch { return false }
}
