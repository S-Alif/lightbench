// badges
const TONE = {
	neutral: 'bg-sunken text-muted',
	ok: 'bg-ok/15 text-ok',
	bad: 'bg-bad/15 text-bad',
	warn: 'bg-warn/15 text-warn',
	accent: 'bg-accent/15 text-accent',
	glass: 'bg-black/55 text-white backdrop-blur',
}

export function Badge({ tone = 'neutral', children, className = '' }) {
	return <span className={`inline-flex items-center gap-1 rounded-full px-2.5 py-1 text-xs font-medium ${TONE[tone]} ${className}`}>{children}</span>
}

export const STATUS = {
	queued: ['Queued', 'neutral'], running: ['Processing', 'accent'], done: ['Done', 'ok'],
	partial: ['Partly done', 'warn'], failed: ['Failed', 'bad'], cancelled: ['Cancelled', 'neutral'],
	error: ['Failed', 'bad'],
}

export function StatusBadge({ status, className }) {
	const [text, tone] = STATUS[status] || [status, 'neutral']
	return <Badge tone={tone} className={className}>{text}</Badge>
}
