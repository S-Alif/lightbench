import { useEffect, useState } from 'react'
import Icon from '../../components/icons/Icon.jsx'
import { btn } from '../../components/ui/buttonStyles.js'
import { Modal } from '../../components/ui/Modal.jsx'

// ---- what is stored inside an image: camera, date, location, prompts ----------------
// load() returns a promise for { fields: [{label, value}], warnings: [text] }
export default function MetadataDialog({ title, load, onClose }) {
	const [data, setData] = useState(null)
	const [error, setError] = useState('')

	useEffect(() => {
		let cancelled = false
		load().then((result) => { if (!cancelled) setData(result) }).catch((loadError) => { if (!cancelled) setError(loadError.message) })
		return () => { cancelled = true }
	}, [])      // eslint-disable-line react-hooks/exhaustive-deps

	return (
		<Modal open onClose={onClose} label="Image details" size="lg">
			<div className="p-5 sm:p-6">
				<div className="mb-4 flex items-start justify-between gap-3">
					<div className="min-w-0">
						<h2 className="text-lg font-semibold">Image details</h2>
						<p className="truncate text-sm text-muted" title={title}>{title}</p>
					</div>
					<button type="button" onClick={onClose} aria-label="Close" className={btn('ghost', 'sm', 'px-2.5')}><Icon name="x" className="size-5" /></button>
				</div>

				{!data && !error && <p className="py-10 text-center text-sm text-muted">Reading the file…</p>}
				{error && <p role="alert" className="py-6 text-sm text-bad">{error}</p>}

				{data && (
					<div className="space-y-4">
						{data.warnings.map((warning) => (
							<p key={warning} role="alert" className="flex gap-3 rounded-2xl bg-warn/12 p-4 text-sm text-warn ring-1 ring-warn/30">
								<Icon name="alert" className="mt-0.5 size-4 shrink-0" />{warning}
							</p>
						))}
						<dl className="divide-y divide-line rounded-2xl ring-1 ring-line">
							{data.fields.map((field, index) => (
								<div key={`${field.label}-${index}`} className="grid gap-1 px-4 py-3 text-sm sm:grid-cols-[10rem_minmax(0,1fr)] sm:gap-4">
									<dt className="text-muted">{field.label}</dt>
									<dd className="min-w-0 break-words font-medium">{field.value}</dd>
								</div>
							))}
						</dl>
						{data.fields.length <= 1 && <p className="text-sm text-muted">No camera, location or other hidden data was found in this file.</p>}
						<p className="text-xs text-muted">Lightbench removes camera and location data from results unless “Keep metadata” is switched on.</p>
					</div>
				)}
			</div>
		</Modal>
	)
}
