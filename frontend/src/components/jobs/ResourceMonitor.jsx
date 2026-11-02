import { useEffect, useState } from 'react'
import { api } from '../../api/client.js'
import { fmtBytes } from '../../lib/format.js'
import { ProgressBar } from '../ui/ProgressBar.jsx'

function Meter({ label, detail, value }) {
	const tone = value > 0.9 ? 'bad' : 'accent'
	return (
		<div className="min-w-0 space-y-1.5">
			<div className="flex items-baseline justify-between gap-2 text-xs">
				<span className="font-medium">{label}</span>
				<span className="tnum truncate text-muted">{detail}</span>
			</div>
			<ProgressBar value={value} tone={tone} className="h-1.5" />
		</div>
	)
}

// ---- live cpu, memory and gpu load, polled once a second while it is on screen ----
export default function ResourceMonitor() {
	const [usage, setUsage] = useState(null)

	useEffect(() => {
		let stop = false
		const read = () => api.usage().then((latest) => { if (!stop) setUsage(latest) }).catch(() => { })
		read()
		const intervalId = setInterval(read, 1000)
		return () => { stop = true; clearInterval(intervalId) }
	}, [])

	if (!usage) return null
	const gpu = usage.gpu
	return (
		<div className="grid gap-x-6 gap-y-3 sm:grid-cols-2 lg:grid-cols-3" aria-label="Resource monitor">
			<Meter label="CPU" detail={`${Math.round(usage.cpu_percent)}%`} value={usage.cpu_percent / 100} />
			<Meter label="Memory" detail={`${fmtBytes(usage.ram_used)} / ${fmtBytes(usage.ram_total)}`} value={usage.ram_used / usage.ram_total} />
			{gpu && (
				<Meter
					label={gpu.percent == null ? 'GPU memory' : `GPU ${Math.round(gpu.percent)}% · memory`}
					detail={`${fmtBytes(gpu.memory_used)} / ${fmtBytes(gpu.memory_total)}`}
					value={gpu.memory_used / gpu.memory_total}
				/>
			)}
		</div>
	)
}
