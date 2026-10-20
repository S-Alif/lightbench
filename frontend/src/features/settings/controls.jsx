import { inputCls } from '../../components/ui/Field.jsx'

export function Slider({ 
	label, 
	value, 
	min, 
	max, 
	step = 1, 
	onChange, format = (amount) => amount 
}) {
	return (
		<label className="flex items-center gap-4">
			<span className="w-20 shrink-0 text-sm text-muted">{label}</span>
			<input 
				type="range" 
				min={min} 
				max={max} 
				step={step} 
				value={value} 
				onChange={(event) => onChange(+event.target.value)} className="h-6 min-w-0 flex-1" 
			/>
			<output className="tnum w-12 shrink-0 text-right text-sm font-medium">{format(value)}</output>
		</label>
	)
}

export function NumberBox({ 
	label, 
	value, 
	onChange, 
	step, 
	suffix 
}) {
	return (
		<label className="block min-w-0 space-y-1.5">
			<span className="block truncate text-xs text-muted">{label}</span>
			<span className="relative block">
				<input 
					type="number" 
					min="0" 
					step={step} 
					value={value} 
					onChange={(event) => onChange(event.target.value === '' ? 0 : Number(event.target.value))}
					className={`${inputCls} tnum pr-10`} 
				/>
				<span className="pointer-events-none absolute inset-y-0 right-3 grid place-items-center text-xs text-muted">{suffix}</span>
			</span>
		</label>
	)
}
