import { useCallback, useEffect, useRef, useState } from 'react'
import Icon from '../components/icons/Icon.jsx'
import { btn } from '../components/ui/buttonStyles.js'
import { Seg } from '../components/ui/Seg.jsx'
import { useToast } from '../components/ui/Toast.jsx'
import { CollagePanel, COLLAGE_DEFAULTS } from '../features/tools/CollagePanel.jsx'
import { ConvertPanel, CONVERT_DEFAULTS } from '../features/tools/ConvertPanel.jsx'
import { FileStrip } from '../features/tools/FileStrip.jsx'
import { PalettePanel } from '../features/tools/PalettePanel.jsx'
import { SaveTo } from '../features/tools/SaveTo.jsx'
import { SplitPanel, SPLIT_DEFAULTS } from '../features/tools/SplitPanel.jsx'
import { useStored } from '../hooks/usePersistentState.js'

const TOOLS = [['convert', 'Convert'], ['collage', 'Collage'], ['split', 'Split'], ['palette', 'Colours']]
const INFO = {
	convert: 'Change format, shrink, compress to a size, adjust colour and remove hidden data such as GPS location. Works on many pictures at once.',
	collage: 'Put several pictures in one grid. Use the arrows on a picture to change the order.',
	split: 'Cut one picture into equal tiles. Uses the first picture.',
	palette: 'Find the main colours of a picture. Uses the first picture.',
}
let nextId = 1

export default function ToolsPage({ system }) {
	const toast = useToast()
	const [tool, setTool] = useStored('lightbench.tools.tool', 'convert')
	const [files, setFiles] = useState([])
	const [convertOptions, setConvertOptions] = useStored('lightbench.tools.convert', CONVERT_DEFAULTS)
	const [collageOptions, setCollageOptions] = useStored('lightbench.tools.collage', COLLAGE_DEFAULTS)
	const [splitOptions, setSplitOptions] = useStored('lightbench.tools.split', SPLIT_DEFAULTS)
	const [save, setSave] = useStored('lightbench.tools.save', { mode: 'download', folder: '' })
	const [dragging, setDragging] = useState(false)
	const inputRef = useRef(null)
	const local = Boolean(system?.local)
	const urls = useRef(new Map())

	const addFiles = useCallback((picked) => {
		const images = [...picked].filter((file) => file.type.startsWith('image/'))
		if (images.length < picked.length) toast('Only pictures can be used here')
		setFiles((current) => [...current, ...images.map((file) => {
			const url = URL.createObjectURL(file)
			const id = nextId++
			urls.current.set(id, url)
			return { id, file, url }
		})])
	}, [toast])
	const remove = (id) => { URL.revokeObjectURL(urls.current.get(id)); urls.current.delete(id); setFiles((current) => current.filter((entry) => entry.id !== id)) }
	const clear = () => { urls.current.forEach((url) => URL.revokeObjectURL(url)); urls.current.clear(); setFiles([]) }
	const move = (index, step) => setFiles((current) => { const copy = [...current]; [copy[index], copy[index + step]] = [copy[index + step], copy[index]]; return copy })
	useEffect(() => () => urls.current.forEach((url) => URL.revokeObjectURL(url)), [])

	const dropProps = {
		onDragOver: (event) => { event.preventDefault(); setDragging(true) },
		onDragLeave: () => setDragging(false),
		onDrop: (event) => { event.preventDefault(); setDragging(false); addFiles(event.dataTransfer.files) },
	}
	const current = tool in { convert: 1, collage: 1, split: 1, palette: 1 } ? tool : 'convert'

	return (
		<div className="space-y-6" {...dropProps}>
			<div>
				<h1 className="text-2xl font-semibold tracking-tight">Picture tools</h1>
				<p className="mt-1 text-sm text-muted">Everyday jobs for pictures. Runs on your computer; nothing is kept after you download or save the results.</p>
			</div>

			{files.length === 0 ? (
				<button type="button" onClick={() => inputRef.current?.click()} className={`grid h-56 w-full place-items-center rounded-3xl border-2 border-dashed text-center transition ${dragging ? 'border-accent bg-accent/10' : 'border-line bg-surface hover:bg-sunken'}`}>
					<span className="space-y-2">
						<Icon name="upload" className="mx-auto size-8 text-muted" />
						<span className="block font-medium">Drop pictures here or click to choose</span>
						<span className="block text-sm text-muted">JPG, PNG, WebP, BMP and TIFF</span>
					</span>
				</button>
			) : (
				<div className={`space-y-3 rounded-3xl bg-surface p-4 ring-1 ${dragging ? 'ring-2 ring-accent' : 'ring-line'}`}>
					<FileStrip files={files} onRemove={remove} onMove={current === 'collage' ? move : undefined} />
					<div className="flex gap-2">
						<button type="button" onClick={() => inputRef.current?.click()} className={btn('secondary', 'sm')}><Icon name="plus" className="size-4" />Add more</button>
						<button type="button" onClick={clear} className={btn('ghost', 'sm')}>Clear all</button>
					</div>
				</div>
			)}
			<input ref={inputRef} type="file" accept="image/*" multiple hidden onChange={(event) => { addFiles(event.target.files); event.target.value = '' }} />

			<div className="space-y-2">
				<div className="max-w-2xl"><Seg label="Tool" value={current} onChange={setTool} options={TOOLS} /></div>
				<p className="text-sm text-muted">{INFO[current]}</p>
			</div>

			{files.length > 0 && (
				<section className="space-y-6 rounded-3xl bg-surface p-5 ring-1 ring-line sm:p-6">
					{current !== 'palette' && <div className="max-w-md"><SaveTo local={local} save={save} setSave={setSave} /></div>}
					{current === 'convert' && <ConvertPanel files={files} options={{ ...CONVERT_DEFAULTS, ...convertOptions }} setOptions={setConvertOptions} save={save} local={local} />}
					{current === 'collage' && <CollagePanel files={files} options={{ ...COLLAGE_DEFAULTS, ...collageOptions }} setOptions={setCollageOptions} save={save} local={local} />}
					{current === 'split' && <SplitPanel entry={files[0]} options={{ ...SPLIT_DEFAULTS, ...splitOptions }} setOptions={setSplitOptions} save={save} local={local} />}
					{current === 'palette' && <PalettePanel entry={files[0]} />}
				</section>
			)}
		</div>
	)
}
