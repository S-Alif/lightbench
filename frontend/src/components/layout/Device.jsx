// display device info
export function Device({ system }) {
	if (!system) return null
	const gpu = system.backend && !['CPU', 'none'].includes(system.backend)
	const text = system.backend === 'none' ? 'PyTorch missing' : gpu ? `${system.backend} · ${system.name}${system.vram_gb ? ` · ${system.vram_gb} GB` : ''}` : 'CPU mode'
	return (
		<span 
			title={`torch ${system.torch || 'n/a'}`}
			className="hidden max-w-[18rem] items-center gap-2 truncate rounded-full bg-surface px-3.5 py-2 text-sm ring-1 ring-line md:inline-flex"
		>
			<span className={`size-2 shrink-0 rounded-full ${gpu ? 'bg-ok' : 'bg-warn'}`} />
			<span className="truncate">{text}</span>
		</span>
	)
}
