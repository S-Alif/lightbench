import { useEffect, useRef, useState } from 'react'

// size of the finished image the preview pretends to be when no file has been picked yet
const REFERENCE_OUTPUT_SIZE = { width: 1600, height: 2133 }

// the preview never gets taller than this share of the screen, so tall images still fit
const PREVIEW_MAX_HEIGHT_VH = 70

// preview of where the text lands. it has the same proportions as the finished image,
// so the text size and margins look like they will in the real file.
// sourceSize = size of the first picked file, scale = the upscale factor (1 = off)
export function WmPreview({ watermark, sourceSize, scale }) {
	const previewRef = useRef(null)
	const [shownWidth, setShownWidth] = useState(0)

	// the output is the picked file times the upscale factor, fixed-pixel values apply to that final size
	const outputSize = sourceSize
		? { width: sourceSize.width * scale, height: sourceSize.height * scale }
		: REFERENCE_OUTPUT_SIZE

	// measure how wide the preview really is on screen, to tell the user how much it is shrunk
	useEffect(() => {
		const previewElement = previewRef.current
		if (!previewElement) return
		const observer = new ResizeObserver(() => setShownWidth(previewElement.clientWidth))
		observer.observe(previewElement)
		setShownWidth(previewElement.clientWidth)
		return () => observer.disconnect()
	}, [])

	const isRelative = watermark.size_mode === 'relative'

	// everything below is in percent of the image, so it scales with the preview
	const fontSizePercent = isRelative ? watermark.font_size : (watermark.font_size / outputSize.width) * 100
	const marginXPercent = isRelative ? watermark.margin_x : (watermark.margin_x / outputSize.width) * 100
	const marginYPercent = isRelative ? watermark.margin_y : (watermark.margin_y / outputSize.height) * 100

	const [row, column] = watermark.position === 'center' ? ['center', 'center'] : watermark.position.split('_')
	const textStyle = { position: 'absolute', whiteSpace: 'nowrap', opacity: watermark.opacity, color: watermark.color, fontWeight: 700, fontSize: `${fontSizePercent}cqw`, lineHeight: 1 }
	const transforms = []

	// horizontal: left / right edge with a margin, or centered
	if (column === 'left') textStyle.left = `${marginXPercent}cqw`
	else if (column === 'right') textStyle.right = `${marginXPercent}cqw`
	else { textStyle.left = '50%'; transforms.push('translateX(-50%)') }

	// vertical: top / bottom edge with a margin, or centered
	if (row === 'top') textStyle.top = `${marginYPercent}%`
	else if (row === 'bottom') textStyle.bottom = `${marginYPercent}%`
	else { textStyle.top = '50%'; transforms.push('translateY(-50%)') }
	if (transforms.length) textStyle.transform = transforms.join(' ')

	// as wide as the panel allows, but never taller than the max height
	const aspectRatio = outputSize.width / outputSize.height
	const boxWidth = `min(100%, ${PREVIEW_MAX_HEIGHT_VH * aspectRatio}vh)`
	const shownPercent = shownWidth ? Math.round((shownWidth / outputSize.width) * 100) : null

	return (
		<div className="w-full">
			<div
				ref={previewRef}
				className="relative mx-auto overflow-hidden rounded-xl ring-1 ring-line"
				style={{ width: boxWidth, aspectRatio: `${outputSize.width} / ${outputSize.height}`, containerType: 'inline-size', background: 'linear-gradient(160deg, #3b4a63 0%, #7a5c8f 55%, #d98a5f 100%)' }}
			>
				<span style={textStyle}>{watermark.text || 'Your text'}</span>
			</div>
			<p className="tnum mt-2 text-center text-xs text-muted">
				{sourceSize ? 'Your' : 'Example'} {Math.round(outputSize.width)}×{Math.round(outputSize.height)} px result
				{shownPercent ? `, shown at ${shownPercent}% of its real size` : ''}
			</p>
		</div>
	)
}
