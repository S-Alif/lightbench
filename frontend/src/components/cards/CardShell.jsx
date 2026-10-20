import Icon from '../icons/Icon.jsx'

// one portrait (3:4) card shell shared by every card in the app - this is for a vibe coder, yes we reuse everything we can
export function CardShell({ children, onClick, className = '', label }) {
	const Tag = onClick ? 'button' : 'div'
	return (
		<Tag 
			type={onClick ? 'button' : undefined} 
			onClick={onClick} aria-label={label}
			className={`group relative block aspect-3/4 w-full overflow-hidden rounded-2xl bg-sunken text-left ring-1 ring-line shadow-card transition 
				${onClick ? 'hover:-translate-y-0.5 hover:ring-accent/60' : ''} ${className}`}
		>
			{children}
		</Tag>
	)
}

export const Scrim = () => <div className="pointer-events-none absolute inset-0 bg-[linear-gradient(to_top,rgb(0_0_0/.88)_0%,rgb(0_0_0/.6)_26%,rgb(0_0_0/0)_55%,rgb(0_0_0/.3)_100%)]" />

export const Empty = ({ kind }) => (
	<div className="absolute inset-0 grid place-items-center text-muted">
		<Icon name={kind === 'video' ? 'video' : 'image'} className="size-10 opacity-50" />
	</div>
)
