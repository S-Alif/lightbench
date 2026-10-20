import Icon from '../icons/Icon.jsx'

export function Section({ title, icon, children, defaultOpen = true, aside }) {
	return (
		<details open={defaultOpen} className="group rounded-2xl bg-surface ring-1 ring-line shadow-card">
			<summary className="flex cursor-pointer list-none items-center gap-3 px-5 py-4 [&::-webkit-details-marker]:hidden">
				{icon && 
					<span className="grid size-9 place-items-center rounded-xl bg-sunken text-accent">
						<Icon name={icon} className="size-5" />
					</span>
				}
				<span className="flex-1 text-base font-semibold">{title}</span>
				{aside}
				<Icon name="right" className="size-4 text-muted transition group-open:rotate-90" />
			</summary>
			<div className="space-y-6 border-t border-line px-5 pb-6 pt-5">{children}</div>
		</details>
	)
}
