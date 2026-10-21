// Tiny stroke-icon set (24px grid). No icon font, nothing to download.
const ICON_PATHS = {
	upload: <><path d="M12 16V4m0 0L7 9m5-5 5 5" /><path d="M4 16v3a1 1 0 0 0 1 1h14a1 1 0 0 0 1-1v-3" /></>,
	download: <><path d="M12 4v12m0 0 5-5m-5 5-5-5" /><path d="M4 16v3a1 1 0 0 0 1 1h14a1 1 0 0 0 1-1v-3" /></>,
	trash: <path d="M4 7h16M10 11v6m4-6v6M6 7l1 12a1 1 0 0 0 1 1h8a1 1 0 0 0 1-1l1-12M9 7V4h6v3" />,
	x: <path d="M6 6l12 12M18 6 6 18" />,
	check: <path d="m5 12 5 5 9-10" />,
	folder: <path d="M3 7a1 1 0 0 1 1-1h5l2 2h8a1 1 0 0 1 1 1v9a1 1 0 0 1-1 1H4a1 1 0 0 1-1-1V7z" />,
	image: <><rect x="3" y="4" width="18" height="16" rx="2" /><circle cx="9" cy="10" r="1.5" /><path d="m21 16-5-5-8 8" /></>,
	video: <><rect x="3" y="5" width="18" height="14" rx="2" /><path d="m10 9 5 3-5 3z" /></>,
	history: <><path d="M3 12a9 9 0 1 0 3-6.7L3 8" /><path d="M3 3v5h5M12 8v4l3 2" /></>,
	sparkles: <><path d="M12 3l1.8 4.7L18.5 9.5l-4.7 1.8L12 16l-1.8-4.7L5.5 9.5l4.7-1.8z" /><path d="M19 15l.8 2.2L22 18l-2.2.8L19 21l-.8-2.2L16 18l2.2-.8z" /></>,
	sun: <><circle cx="12" cy="12" r="4" /><path d="M12 2v2m0 16v2M2 12h2m16 0h2M5 5l1.4 1.4m11.2 11.2L19 19M19 5l-1.4 1.4M6.4 17.6 5 19" /></>,
	moon: <path d="M20 14.5A8 8 0 1 1 9.5 4a6.5 6.5 0 0 0 10.5 10.5z" />,
	copy: <><rect x="9" y="9" width="11" height="11" rx="2" /><path d="M5 15V5a1 1 0 0 1 1-1h10" /></>,
	refresh: <path d="M20 11a8 8 0 0 0-14.5-3M4 5v4h4M4 13a8 8 0 0 0 14.5 3M20 19v-4h-4" />,
	left: <path d="m15 5-7 7 7 7" />,
	right: <path d="m9 5 7 7-7 7" />,
	alert: <><path d="M12 4 2.5 20h19z" /><path d="M12 10v4m0 3v.01" /></>,
	chip: <><rect x="6" y="6" width="12" height="12" rx="2" /><path d="M9 2v4m6-4v4M9 18v4m6-4v4M2 9h4m-4 6h4m12-6h4m-4 6h4" /></>,
	crop: <><path d="M6 2v14a2 2 0 0 0 2 2h14" /><path d="M2 6h14a2 2 0 0 1 2 2v14" /></>,
	rotateLeft: <><path d="M4 4v5h5" /><path d="M4.5 9A8 8 0 1 1 4 13" /></>,
	rotateRight: <><path d="M20 4v5h-5" /><path d="M19.5 9A8 8 0 1 0 20 13" /></>,
	plus: <path d="M12 5v14M5 12h14" />,
	play: <path d="M8 5v14l11-7z" fill="currentColor" />,
	info: <><circle cx="12" cy="12" r="9" /><path d="M12 11v5m0-8v.01" /></>,
}

export default function Icon({ name, className = 'size-5', ...rest }) {
	return (
		<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round"
			strokeLinejoin="round" className={className} aria-hidden="true" {...rest}>
			{ICON_PATHS[name]}
		</svg>
	)
}
