export function Switch({ checked, onChange, title, hint }) {
	return (
		<label className="flex cursor-pointer items-start gap-3">
			<span className="relative mt-0.5 inline-flex h-6 w-11 shrink-0">
				<input type="checkbox" role="switch" checked={checked} onChange={(event) => onChange(event.target.checked)} className="peer sr-only" />
				<span className="absolute inset-0 rounded-full bg-sunken ring-1 ring-line transition peer-checked:bg-accent peer-checked:ring-accent peer-focus-visible:outline-2 peer-focus-visible:outline-offset-2 peer-focus-visible:outline-accent" />
				<span className="absolute left-1 top-1 size-4 rounded-full bg-muted transition peer-checked:translate-x-5 peer-checked:bg-accent-ink" />
			</span>
			<span className="min-w-0">
				<span className="block text-[15px] font-medium leading-6">{title}</span>
				{hint && <span className="block text-sm leading-5 text-muted">{hint}</span>}
			</span>
		</label>
	)
}
