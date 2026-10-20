// a banner to display some info
export function Banner({ tone = 'warn', children }) {
	return (
		<p className={`mb-6 rounded-2xl px-5 py-3.5 text-sm ring-1 ${tone === 'warn' ? 'bg-warn/12 text-warn ring-warn/30' : 'bg-surface text-muted ring-line'}`}>
			{children}
		</p>
	)
}
