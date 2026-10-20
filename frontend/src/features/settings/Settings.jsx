import Icon from '../../components/icons/Icon.jsx'
import { Field, inputCls } from '../../components/ui/Field.jsx'
import { Section } from '../../components/ui/Section.jsx'
import { Seg } from '../../components/ui/Seg.jsx'
import { Switch } from '../../components/ui/Switch.jsx'
import { modelProblem, resolveFile } from '../../lib/models.js'
import { NumberBox, Slider } from './controls.jsx'
import { POSITIONS, WM_PRESETS } from './defaults.js'
import { WmPreview } from './WatermarkPreview.jsx'

// settings
export default function Settings({ 
	opts, 
	setOpts, 
	models, 
	modelsDir, 
	onRefreshModels, 
	refreshing, 
	sourceSize,
	disabled 
}) {
	const set = (patch) => setOpts((currentOptions) => ({ ...currentOptions, ...patch }))
	const setWm = (patch) => setOpts((currentOptions) => ({ ...currentOptions, wm: { ...currentOptions.wm, ...patch } }))
	const rel = opts.wm.size_mode === 'relative'

	const custom = models.filter((m) => !m.builtin)
	const selValue = opts.model === 'auto' ? opts.profile : `file:${opts.model}`
	const onModel = (selection) => (selection.startsWith('file:') ? set({ model: selection.slice(5) }) : set({ model: 'auto', profile: selection }))

	const file = resolveFile(opts)
	const info = models.find((model) => model.file === file)
	const problem = modelProblem(opts, models)
	const native = info?.net_scale

	return (
		<fieldset disabled={disabled} className="min-w-0 space-y-5 disabled:opacity-60">
			<Section title="Model & scale" icon="sparkles">
				<Field label="Model" hint={custom.length ? `${custom.length} custom` : undefined}>
					<div className="flex gap-2">
						<select 
							value={selValue} 
							onChange={(event) => onModel(event.target.value)} 
							className={`${inputCls} flex-1`} 
							aria-label="Model"
						>
							<optgroup label="Built in (automatic weights)">
								<option value="photo">Photo / realistic</option>
								<option value="art">Art / illustration</option>
							</optgroup>
							{custom.length > 0 && (
								<optgroup label="Your models (models folder)">
									{custom.map((customModel) => (
										<option key={customModel.file} value={`file:${customModel.file}`} disabled={customModel.ok === false}>
											{customModel.label}{customModel.ok ? ` · ${customModel.net_scale}×` : customModel.ok === false ? ' · unsupported' : ''}
										</option>
									))}
								</optgroup>
							)}
						</select>

						{/* refresh models btn */}
						<button 
							type="button" 
							onClick={onRefreshModels} 
							title="Re-scan the models folder" aria-label="Re-scan the models folder"
							className="grid size-11 shrink-0 place-items-center rounded-xl bg-surface text-muted ring-1 ring-line transition hover:bg-sunken hover:text-ink"
						>
							<Icon name="refresh" className={`size-5 ${refreshing ? 'animate-spin' : ''}`} />
						</button>
					</div>

					{problem ? (
						<p className="flex gap-2 rounded-xl bg-bad/10 p-3 text-sm text-bad"><Icon name="alert" className="mt-0.5 size-4 shrink-0" />{problem}</p>
					) : opts.scale === 1 ? (
						<p className="text-sm text-muted">Upscaling is off, so no model is used.</p>
					) : (
						<p className="text-sm leading-relaxed text-muted">
							Uses <code className="rounded bg-sunken px-1.5 py-0.5 font-mono text-xs text-ink">{file}</code>
							{info && !info.present && info.builtin && <> (downloads on first use)</>}
							{native && native !== opts.scale && <>, native {native}× then resized to {opts.scale}×</>}.
						</p>
					)}
					<p className="text-xs leading-relaxed text-muted">
						Add your own <code className="font-mono">.pth</code> files to <code className="break-all font-mono">{modelsDir || 'the models folder'}</code>, then press refresh. Real-ESRGAN (RRDBNet) and compact (SRVGG) models are supported.
					</p>
				</Field>

				<Field label="Upscale" hint={opts.scale === 1 ? 'watermark / convert only' : undefined}>
					<Seg 
						label="Upscale factor" 
						value={opts.scale} 
						onChange={(scale) => set({ scale })}
						options={[[1, 'Off'], [2, '2×'], [3, '3×'], [4, '4×']]} 
					/>
				</Field>
			</Section>

			<Section title="Output" icon="image">
				<Field label="Image format">
					<Seg 
						label="Image format" 
						value={opts.fmt} 
						onChange={(fmt) => set({ fmt })}
						options={[['jpg', 'JPG'], ['png', 'PNG'], ['webp', 'WebP']]} 
					/>
					{opts.fmt !== 'png' && 
						<Slider 
							label="Quality" 
							min={60} 
							max={100} 
							value={opts.quality} 
							onChange={(quality) => set({ quality })} 
						/>
					}
					<p className="text-xs text-muted">Videos are always saved as H.264 MP4 with the original audio.</p>
				</Field>
				<Switch 
					checked={opts.keep_metadata} 
					onChange={(keep_metadata) => set({ keep_metadata })} 
					title="Keep metadata"
					hint="EXIF and PNG text such as generation prompts. Off removes them, which is better for privacy." 
				/>
			</Section>

			<Section 
				title="Watermark" 
				icon="sparkles"
				aside={<span className={`text-xs font-medium ${opts.wm_on ? 'text-accent' : 'text-muted'}`}>{opts.wm_on ? 'On' : 'Off'}</span>}
			>
				<Switch 
					checked={opts.wm_on} 
					onChange={(wm_on) => set({ wm_on })} 
					title="Add a text watermark" 
				/>
				{opts.wm_on && (
					<div className="space-y-6">
						<Field label="Text">
							<input 
								type="text" 
								className={inputCls} 
								placeholder="e.g. @yourname" 
								value={opts.wm.text} 
								onChange={(event) => setWm({ text: event.target.value })} 
							/>
						</Field>

						<Field label="Position" className="shrink-0">
							<div role="radiogroup" aria-label="Watermark position" className="grid w-fit grid-cols-3 gap-1.5 rounded-xl bg-sunken p-2">
								{POSITIONS.map((position) => (
									<button 
										key={position} 
										type="button" 
										role="radio" 
										aria-checked={opts.wm.position === position} 
										aria-label={position.replace('_', ' ')}
										onClick={() => setWm({ position: position })}
										className={`h-8 w-9 rounded-md ring-1 transition ${opts.wm.position === position ? 'bg-accent ring-accent' : 'bg-surface ring-line hover:ring-muted'}`} 
									/>
								))}
							</div>
						</Field>

						{/* the preview gets its own full width row so it can be shown big */}
						<WmPreview watermark={opts.wm} sourceSize={sourceSize} scale={opts.scale} />
						<div className="space-y-4">
							<Slider 
								label="Opacity" 
								min={5} 
								max={100} 
								value={Math.round(opts.wm.opacity * 100)} 
								onChange={(percent) => setWm({ opacity: percent / 100 })} 
								format={(percent) => `${percent}%`} 
							/>
							<label className="flex items-center gap-4">
								<span className="w-20 shrink-0 text-sm text-muted">Color</span>
								<input 
									type="color" 
									value={opts.wm.color} 
									onChange={(event) => setWm({ color: event.target.value })}
									className="h-10 w-16 cursor-pointer rounded-lg bg-transparent p-0 ring-1 ring-line" aria-label="Watermark color" 
								/>
							</label>
						</div>

						<Field 
							label="Size" 
							hint={rel ? 'scales with the image' : 'same pixels on every image'}
						>
							<Seg 
								label="Watermark size mode" 
								value={opts.wm.size_mode} 
								onChange={(size_mode) => setWm({ size_mode, ...WM_PRESETS[size_mode] })}
								options={[['relative', 'Relative'], ['pixels', 'Fixed pixels']]} 
							/>

							<div className="grid grid-cols-3 gap-3">
								<NumberBox 
									label="Text size" 
									value={opts.wm.font_size} 
									step={rel ? 0.1 : 1} 
									suffix={rel ? '% w' : 'px'} 
									onChange={(font_size) => setWm({ font_size })} 
								/>

								<NumberBox 
									label="Margin X" 
									value={opts.wm.margin_x} 
									step={rel ? 0.5 : 1} 
									suffix={rel ? '% w' : 'px'} 
									onChange={(margin_x) => setWm({ margin_x })} 
								/>

								<NumberBox 
									label="Margin Y" 
									value={opts.wm.margin_y} 
									step={rel ? 0.5 : 1} 
									suffix={rel ? '% h' : 'px'} 
									onChange={(margin_y) => setWm({ margin_y })} 
								/>
							</div>
							<p className="text-xs text-muted">Relative sizing keeps the watermark looking the same at 2×, 3× and 4×.</p>
						</Field>
					</div>
				)}
			</Section>

			<Section 
				title="Advanced" 
				icon="chip" 
				defaultOpen={false}
			>
				<Field 
					label="Tile size" 
					hint="smaller = less VRAM, slower"
				>
					<select 
						value={opts.tile} 
						onChange={(event) => set({ tile: +event.target.value })} 
						className={inputCls} aria-label="Tile size"
					>
						<option value={0}>No tiling (needs lots of VRAM)</option>
						<option value={1024}>1024</option>
						<option value={512}>512 (default)</option>
						<option value={256}>256</option>
						<option value={128}>128</option>
					</select>
					<p className="text-xs text-muted">Out-of-memory errors automatically retry with smaller tiles.</p>
				</Field>
				<Switch 
					checked={opts.fp32} 
					onChange={(fp32) => set({ fp32 })} 
					title="Full precision (fp32)"
					hint="Turn on if results come out green or black (some GTX 16-series cards). Slower, uses more VRAM." 
				/>
				<Field 
					label="Video quality" 
					hint="lower = better, bigger file"
				>
					<Slider 
						label="CRF" 
						min={12} 
						max={28} 
						value={opts.video_crf} 
						onChange={(video_crf) => set({ video_crf })} 
					/>
				</Field>
				<Field label="Video encode speed">
					<select 
						value={opts.video_preset} 
						onChange={(event) => set({ video_preset: event.target.value })} 
						className={inputCls} aria-label="Video encode speed"
					>
						{['veryfast', 'fast', 'medium', 'slow'].map((preset) => <option key={preset} value={preset}>{preset}</option>)}
					</select>
				</Field>
			</Section>
		</fieldset>
	)
}
