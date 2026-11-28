import { Field, inputCls } from '../../components/ui/Field.jsx'
import { Seg } from '../../components/ui/Seg.jsx'

// where results go: the browser's download, or (on the computer that runs the app) a folder
export function SaveTo({ local, save, setSave }) {
	if (!local) return null
	return (
		<Field label="Save results" hint={save.mode === 'folder' ? 'Files are written straight into this folder. Nothing is overwritten.' : 'Your browser downloads them'}>
			<Seg label="Save results" value={save.mode} onChange={(mode) => setSave((current) => ({ ...current, mode }))} options={[['download', 'Download'], ['folder', 'To a folder']]} />
			{save.mode === 'folder' && (
				<input type="text" value={save.folder} onChange={(event) => setSave((current) => ({ ...current, folder: event.target.value }))}
					placeholder="/home/you/Pictures/Lightbench" aria-label="Folder" spellCheck={false} className={`${inputCls} mt-2`} />
			)}
		</Field>
	)
}

export const saveTarget = (save, local) => (local && save.mode === 'folder' ? save.folder.trim() : null)
export const folderMissing = (save, local) => local && save.mode === 'folder' && !save.folder.trim()
