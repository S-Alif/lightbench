export const fmtBytes = (bytes = 0) =>
	bytes >= 1e9 ? `${(bytes / 1e9).toFixed(2)} GB` : bytes >= 1e6 ? `${(bytes / 1e6).toFixed(1)} MB` : bytes > 0 ? `${Math.max(1, Math.round(bytes / 1e3))} KB` : '0 KB'

export const fmtDate = (timestamp) =>
	timestamp ? new Date(timestamp * 1000).toLocaleString(undefined, { dateStyle: 'medium', timeStyle: 'short' }) : ''

// 83 -> "1:23", 3700 -> "1:01:40"
export const fmtClock = (totalSeconds) => {
	totalSeconds = Math.max(0, Math.round(totalSeconds || 0))
	const hours = Math.floor(totalSeconds / 3600), minutes = Math.floor((totalSeconds % 3600) / 60), sec = totalSeconds % 60
	const pad = (number) => String(number).padStart(2, '0')
	return hours ? `${hours}:${pad(minutes)}:${pad(sec)}` : `${minutes}:${pad(sec)}`
}

export const plural = (count, word) => `${count} ${word}${count === 1 ? '' : 's'}`
