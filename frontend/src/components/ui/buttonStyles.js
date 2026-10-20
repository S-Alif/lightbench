// ---- buttons -------------------------------------------------------------
const BTN_BASE = 'inline-flex items-center justify-center gap-2 rounded-xl font-medium transition active:scale-[.98] disabled:opacity-45 disabled:pointer-events-none select-none whitespace-nowrap'

const BTN_VARIANT = {
	primary: 'bg-accent text-accent-ink hover:brightness-110 shadow-sm',
	secondary: 'bg-surface text-ink ring-1 ring-line hover:bg-sunken',
	ghost: 'text-muted hover:text-ink hover:bg-sunken',
	danger: 'bg-bad text-white hover:brightness-110',
	dangerSoft: 'text-bad ring-1 ring-bad/40 hover:bg-bad/10',
}

const BTN_SIZE = { sm: 'h-9 px-3 text-sm', md: 'h-11 px-5 text-[15px]', lg: 'h-12 px-6 text-base' }

export const btn = (variant = 'secondary', size = 'md', extra = '') => `${BTN_BASE} ${BTN_VARIANT[variant]} ${BTN_SIZE[size]} ${extra}`
