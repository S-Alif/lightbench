// crop shapes offered in the editor
// a platform name is shown only when the ratio is that platform's own guidance;
// every other ratio is just written as the ratio.
const PLATFORM_NAMES = {
	'1:1': 'Square',
	'4:5': 'Instagram post',
	'2:3': 'Pinterest pin',
	'9:16': 'Stories · Reels · TikTok',
	'16:9': 'YouTube',
}

export const RATIO_PRESETS = [
	{ id: 'original', title: 'Original', ratio: 'original' },
	{ id: '1:1', width: 1, height: 1 },
	{ id: '4:5', width: 4, height: 5 },
	{ id: '3:4', width: 3, height: 4 },
	{ id: '2:3', width: 2, height: 3 },
	{ id: '9:16', width: 9, height: 16 },
	{ id: '16:9', width: 16, height: 9 },
	{ id: '3:2', width: 3, height: 2 },
	{ id: '4:3', width: 4, height: 3 },
]

// "4:5 · Instagram post" or just "3:4"
export function ratioLabel(width, height) {
	const key = `${width}:${height}`
	return PLATFORM_NAMES[key] ? `${key} · ${PLATFORM_NAMES[key]}` : key
}

export function platformName(width, height) {
	return PLATFORM_NAMES[`${width}:${height}`] || ''
}
