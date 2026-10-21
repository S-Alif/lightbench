// models
const AUTO = {
	photo: { 2: 'RealESRGAN_x2plus.pth', 3: 'RealESRGAN_x4plus.pth', 4: 'RealESRGAN_x4plus.pth' },
	art: { 2: 'RealESRGAN_x4plus_anime_6B.pth', 3: 'RealESRGAN_x4plus_anime_6B.pth', 4: 'RealESRGAN_x4plus_anime_6B.pth' },
}

// file the backend will use for these options
export const resolveFile = (options) => (options.model && options.model !== 'auto' ? options.model : AUTO[options.profile]?.[options.scale] || null)

export function modelLabel(options, models = []) {
	if (options.model && options.model !== 'auto') {
		const matchingModel = models.find((model) => model.file === options.model)
		return matchingModel ? matchingModel.label : options.model.replace(/\.pth?$/i, '')
	}
	return options.profile === 'art' ? 'Art / illustration' : 'Photo / realistic'
}

// Something that would make the job fail, or null.
export function modelProblem(options, models) {
	if (options.scale === 1) return null
	const file = resolveFile(options)
	const matchingModel = models.find((model) => model.file === file)
	if (options.model !== 'auto' && !matchingModel) return `${options.model} isn't in the models folder any more. Pick another model or press refresh.`
	if (matchingModel && matchingModel.ok === false) return matchingModel.error || 'This model file is not supported.'
	return null
}
