// ---- form pieces ---------------------------------------------------------
export function Seg({ value, options, onChange, disabled, label }) {
	return (
		<div role="radiogroup" aria-label={label} className="grid auto-cols-fr grid-flow-col gap-1 rounded-xl bg-sunken p-1">
			{options.map(([optionValue, text]) => (
				<button key={String(optionValue)} type="button" role="radio" aria-checked={value === optionValue} disabled={disabled}
					onClick={() => onChange(optionValue)}
					className={`h-9 rounded-lg px-2 text-sm font-medium transition ${value === optionValue ? 'bg-surface text-ink shadow-sm ring-1 ring-line' : 'text-muted hover:text-ink'}`}>
					{text}
				</button>
			))}
		</div>
	)
}
