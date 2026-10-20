export const IMG_EXT = ['.png', '.jpg', '.jpeg', '.webp', '.bmp', '.tif', '.tiff']

export const VID_EXT = ['.mp4', '.mov', '.mkv', '.webm', '.avi', '.m4v']

const extOf = (fileName) => fileName.slice(fileName.lastIndexOf('.')).toLowerCase()

export const kindOf = (name) => (IMG_EXT.includes(extOf(name)) ? 'image' : VID_EXT.includes(extOf(name)) ? 'video' : null)

// reads the pixel size of a picked image or video from its object url, resolves { width, height }
export const readMediaSize = (url, kind) =>
	new Promise((resolve, reject) => {
		const mediaElement = document.createElement(kind === 'video' ? 'video' : 'img')
		mediaElement.onerror = () => reject(new Error('Could not read the file size'))
		if (kind === 'video') {
			mediaElement.preload = 'metadata'
			mediaElement.onloadedmetadata = () => resolve({ width: mediaElement.videoWidth, height: mediaElement.videoHeight })
		} else {
			mediaElement.onload = () => resolve({ width: mediaElement.naturalWidth, height: mediaElement.naturalHeight })
		}
		mediaElement.src = url
	})
