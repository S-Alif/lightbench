// each preset is a full set of tracing options; sliders then adjust them
const base = { colormode: 'color', remove_specks: 6, corners: 60, curves: 'spline', layering: 'stacked', detail: 4, smoothing: 1, merge_small: 6 }

export const PRESETS = {
	logo: { label: 'Logo / print', hint: 'Few flat colours, crisp edges. Best for t-shirt designs', options: { ...base, colors: 6, remove_specks: 8 } },
	illustration: { label: 'Illustration', hint: 'Balanced for drawings and flat art', options: { ...base, colors: 12 } },
	detailed: { label: 'Detailed', hint: 'Many colours for rich art, bigger file', options: { ...base, colors: 24, remove_specks: 3, corners: 45, detail: 3.5, smoothing: 0.6, merge_small: 3 } },
	bw: { label: 'Black & white', hint: 'Line art, signatures, stencils', options: { ...base, colormode: 'binary' } },
}

export const DEFAULT_PRESET = 'logo'

// slider definitions: [option key, label, min, max, step, hint]
export const SLIDERS = [
	['colors', 'Colours', 2, 32, 1, 'size of the colour palette'],
	['smoothing', 'Edge smoothing', 0, 3, 0.1, 'higher is smoother, softer corners'],
	['merge_small', 'Merge small shapes', 0, 40, 1, '0 is off, higher means fewer shapes'],
	['remove_specks', 'Remove specks', 0, 64, 1, 'ignore tiny blobs'],
	['corners', 'Sharp corners', 0, 180, 1, 'higher keeps more corners'],
	['detail', 'Simplify shapes', 3.5, 10, 0.5, 'higher is simpler'],
]
