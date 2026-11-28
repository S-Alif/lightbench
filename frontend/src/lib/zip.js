// builds a .zip in the browser (files are stored, not compressed: pictures are already compressed)
const crcTable = (() => {
	const table = new Uint32Array(256)
	for (let index = 0; index < 256; index++) {
		let value = index
		for (let bit = 0; bit < 8; bit++) value = value & 1 ? 0xedb88320 ^ (value >>> 1) : value >>> 1
		table[index] = value >>> 0
	}
	return table
})()

const crc32 = (bytes) => {
	let crc = 0xffffffff
	for (let index = 0; index < bytes.length; index++) crc = crcTable[(crc ^ bytes[index]) & 0xff] ^ (crc >>> 8)
	return (crc ^ 0xffffffff) >>> 0
}

// entries: [{ name, blob }]  ->  Blob
export async function makeZip(entries) {
	const encoder = new TextEncoder()
	const parts = [], central = []
	let offset = 0
	const now = new Date()
	const time = (now.getHours() << 11) | (now.getMinutes() << 5) | (now.getSeconds() >> 1)
	const date = ((now.getFullYear() - 1980) << 9) | ((now.getMonth() + 1) << 5) | now.getDate()
	for (const { name, blob } of entries) {
		const data = new Uint8Array(await blob.arrayBuffer())
		const nameBytes = encoder.encode(name)
		const crc = crc32(data)
		const local = new DataView(new ArrayBuffer(30))
		local.setUint32(0, 0x04034b50, true); local.setUint16(4, 20, true); local.setUint16(6, 0x0800, true)
		local.setUint16(10, time, true); local.setUint16(12, date, true)
		local.setUint32(14, crc, true); local.setUint32(18, data.length, true); local.setUint32(22, data.length, true)
		local.setUint16(26, nameBytes.length, true)
		parts.push(local, nameBytes, data)
		const entry = new DataView(new ArrayBuffer(46))
		entry.setUint32(0, 0x02014b50, true); entry.setUint16(4, 20, true); entry.setUint16(6, 20, true); entry.setUint16(8, 0x0800, true)
		entry.setUint16(12, time, true); entry.setUint16(14, date, true)
		entry.setUint32(16, crc, true); entry.setUint32(20, data.length, true); entry.setUint32(24, data.length, true)
		entry.setUint16(28, nameBytes.length, true); entry.setUint32(42, offset, true)
		central.push(entry, nameBytes)
		offset += 30 + nameBytes.length + data.length
	}
	const centralSize = central.reduce((sum, piece) => sum + piece.byteLength, 0)
	const end = new DataView(new ArrayBuffer(22))
	end.setUint32(0, 0x06054b50, true); end.setUint16(8, entries.length, true); end.setUint16(10, entries.length, true)
	end.setUint32(12, centralSize, true); end.setUint32(16, offset, true)
	return new Blob([...parts, ...central, end], { type: 'application/zip' })
}

export function downloadBlob(blob, name) {
	const url = URL.createObjectURL(blob)
	const link = document.createElement('a')
	link.href = url
	link.download = name
	link.click()
	setTimeout(() => URL.revokeObjectURL(url), 10000)
}

// "photo.jpg" taken twice becomes "photo.jpg" and "photo-2.jpg"
export function uniqueNames(names) {
	const seen = new Map()
	return names.map((name) => {
		const count = (seen.get(name) || 0) + 1
		seen.set(name, count)
		if (count === 1) return name
		const dot = name.lastIndexOf('.')
		return dot > 0 ? `${name.slice(0, dot)}-${count}${name.slice(dot)}` : `${name}-${count}`
	})
}
