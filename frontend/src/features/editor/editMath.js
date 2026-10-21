// ---- crop and rotate maths ------------------------------------------------
// all crop numbers are fractions (0 to 1) of the rotated image, the same
// convention the backend uses, so the preview and the output always agree.

export const FULL_CROP = { x: 0, y: 0, width: 1, height: 1 }
const MIN_SIDE_PIXELS = 16

export const rotatedSize = (width, height, rotate) => (rotate % 180 === 0 ? { width, height } : { width: height, height: width })

export const turn = (rotate, direction) => (rotate + (direction > 0 ? 90 : 270)) % 360

export const isFullCrop = (crop) => crop.x < 1e-6 && crop.y < 1e-6 && crop.width > 1 - 1e-6 && crop.height > 1 - 1e-6

// the edit object sent to the server, or null when nothing changes
export function toEdit(rotate, crop) {
	const full = isFullCrop(crop)
	if (rotate === 0 && full) return null
	return { rotate, crop: full ? null : { ...crop } }
}

// size in pixels after applying an edit to an image of the given size
export function editedSize(width, height, edit) {
	if (!edit) return { width, height }
	const turned = rotatedSize(width, height, edit.rotate)
	if (!edit.crop) return turned
	return {
		width: Math.max(1, Math.round(edit.crop.width * turned.width)),
		height: Math.max(1, Math.round(edit.crop.height * turned.height)),
	}
}

// the biggest centred crop of a given shape that fits inside the image
export function fitRatio(ratioWidth, ratioHeight, imageWidth, imageHeight) {
	const shape = (ratioWidth / ratioHeight) * (imageHeight / imageWidth)   // width fraction / height fraction
	let width = Math.min(1, shape)
	let height = width / shape
	if (height > 1) { height = 1; width = shape }
	return { x: (1 - width) / 2, y: (1 - height) / 2, width, height }
}

const clamp = (value, low, high) => Math.min(high, Math.max(low, value))

// move the whole box, keeping it inside the image
export function moveCrop(start, deltaX, deltaY) {
	return {
		...start,
		x: clamp(start.x + deltaX, 0, 1 - start.width),
		y: clamp(start.y + deltaY, 0, 1 - start.height),
	}
}

// drag a handle. handle is one of n s e w ne nw se sw.
// ratio is null for free roam, or { width, height } to keep a fixed shape (corners only).
export function resizeCrop(start, handle, pointer, imageSize, ratio) {
	const minWidth = MIN_SIDE_PIXELS / imageSize.width
	const minHeight = MIN_SIDE_PIXELS / imageSize.height
	const px = clamp(pointer.x, 0, 1)
	const py = clamp(pointer.y, 0, 1)

	if (ratio && handle.length === 2) {
		const goesRight = handle.includes('e')
		const goesDown = handle.includes('s')
		const anchorX = goesRight ? start.x : start.x + start.width
		const anchorY = goesDown ? start.y : start.y + start.height
		const shape = (ratio.width / ratio.height) * (imageSize.height / imageSize.width)
		const room = { x: goesRight ? 1 - anchorX : anchorX, y: goesDown ? 1 - anchorY : anchorY }
		let width = Math.max(Math.abs(px - anchorX), Math.abs(py - anchorY) * shape)
		width = clamp(width, Math.max(minWidth, minHeight * shape), Math.max(Math.min(room.x, room.y * shape), 1e-6))
		const height = width / shape
		return { x: goesRight ? anchorX : anchorX - width, y: goesDown ? anchorY : anchorY - height, width, height }
	}

	let { x, y, width, height } = start
	const right = x + width
	const bottom = y + height
	if (handle.includes('w')) { x = clamp(px, 0, right - minWidth); width = right - x }
	if (handle.includes('e')) { width = clamp(px, x + minWidth, 1) - x }
	if (handle.includes('n')) { y = clamp(py, 0, bottom - minHeight); height = bottom - y }
	if (handle.includes('s')) { height = clamp(py, y + minHeight, 1) - y }
	return { x, y, width, height }
}
