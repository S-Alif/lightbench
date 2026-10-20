export const DEFAULTS = {
	model: 'auto',
	profile: 'photo',
	scale: 2,
	fmt: 'jpg',
	quality: 95,
	keep_metadata: false,
	tile: 512,
	fp32: false,
	video_crf: 18,
	video_preset: 'medium',
	wm_on: false,
	wm: {
		text: '',
		position: 'bottom_right',
		opacity: 0.5,
		color: '#ffffff',
		size_mode: 'relative',
		font_size: 3,
		margin_x: 6,
		margin_y: 8,
	},
}

export const WM_PRESETS = {
	relative: { 
		font_size: 3, 
		margin_x: 6, 
		margin_y: 8 
	},
	pixels: { 
		font_size: 50, 
		margin_x: 100, 
		margin_y: 200 
	}, // the values from the original script
}

export const POSITIONS = [
	'top_left', 'top_center', 'top_right',
	'center_left', 'center', 'center_right',
	'bottom_left', 'bottom_center', 'bottom_right',
]

export function toPayload(options) {
	const { wm_on, wm: watermark, ...rest } = options
	return { ...rest, watermark: wm_on && watermark.text.trim() ? watermark : null }
}
