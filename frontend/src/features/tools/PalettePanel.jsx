import { useEffect, useState } from 'react'
import { api } from '../../api/client.js'
import { btn } from '../../components/ui/buttonStyles.js'
import { useToast } from '../../components/ui/Toast.jsx'
import { copyText } from '../../lib/clipboard.js'
import { Slider } from '../settings/controls.jsx'

// the main colours of a picture; click one to copy its code
export function PalettePanel({ entry }) {
	const toast = useToast()
	const [count, setCount] = useState(6)
	const [colours, setColours] = useState([])
	const [error, setError] = useState('')

	useEffect(() => {
		if (!entry) return
		const controller = new AbortController()
		const timer = setTimeout(() => {
			api.toolsPalette(entry.file, count, controller.signal).then((found) => { setColours(found); setError('') })
				.catch((failure) => { if (failure.name !== 'AbortError') setError(failure.message) })
		}, 250)
		return () => { clearTimeout(timer); controller.abort() }
	}, [entry, count])

	const copy = async (text) => toast((await copyText(text)) ? `Copied ${text}` : 'Could not copy')
	return (
		<div className="space-y-5">
			<div className="max-w-md"><Slider label="Colours" min={2} max={12} value={count} onChange={setCount} /></div>
			{error && <p role="alert" className="text-sm text-bad">{error}</p>}
			{colours.length > 0 && (
				<>
					<div className="flex h-16 overflow-hidden rounded-2xl ring-1 ring-line">
						{colours.map((colour) => <button key={colour.hex} type="button" onClick={() => copy(colour.hex)} aria-label={`Copy ${colour.hex}`} style={{ background: colour.hex, flexGrow: Math.max(colour.share, 0.04) }} />)}
					</div>
					<ul className="grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
						{colours.map((colour) => (
							<li key={colour.hex}>
								<button type="button" onClick={() => copy(colour.hex)} className="flex w-full items-center gap-3 rounded-xl bg-surface p-2 text-left ring-1 ring-line hover:bg-sunken">
									<span className="size-10 shrink-0 rounded-lg ring-1 ring-black/10" style={{ background: colour.hex }} />
									<span className="tnum font-mono text-sm font-medium uppercase">{colour.hex}</span>
									<span className="tnum ml-auto text-sm text-muted">{Math.round(colour.share * 100)}%</span>
								</button>
							</li>
						))}
					</ul>
					<button type="button" onClick={() => copy(colours.map((colour) => colour.hex).join(', '))} className={btn('secondary', 'sm')}>Copy all codes</button>
				</>
			)}
		</div>
	)
}
