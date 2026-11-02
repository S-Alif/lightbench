import { useState } from 'react'
import { api } from '../api/client.js'
import Icon from '../components/icons/Icon.jsx'
import { btn } from '../components/ui/buttonStyles.js'
import { inputCls } from '../components/ui/Field.jsx'

// ---- shown to other devices on the network until they enter the password ---------
export default function LoginPage({ onLoggedIn }) {
	const [password, setPassword] = useState('')
	const [error, setError] = useState('')
	const [busy, setBusy] = useState(false)

	const submit = async (submitEvent) => {
		submitEvent.preventDefault()
		setBusy(true)
		setError('')
		try {
			await api.login(password)
			onLoggedIn()
		} catch (loginError) {
			setError(loginError.message)
			setBusy(false)
		}
	}

	return (
		<main className="grid min-h-screen place-items-center px-4">
			<form onSubmit={submit} className="w-full max-w-sm space-y-5 rounded-3xl bg-surface p-7 ring-1 ring-line shadow-xl">
				<div className="flex items-center gap-3">
					<span className="grid size-10 place-items-center rounded-xl bg-accent text-accent-ink shadow-sm"><Icon name="sparkles" className="size-5" /></span>
					<h1 className="text-xl font-semibold tracking-tight">Lightbench</h1>
				</div>
				<div>
					<label htmlFor="lightbench-password" className="mb-1.5 block text-sm font-medium">Password</label>
					<input
						id="lightbench-password"
						type="password"
						autoFocus
						autoComplete="current-password"
						value={password}
						onChange={(changeEvent) => setPassword(changeEvent.target.value)}
						className={inputCls}
					/>
					<p className="mt-2 text-xs text-muted">It is shown in the terminal window that started Lightbench.</p>
				</div>
				{error && <p role="alert" className="text-sm text-bad">{error}</p>}
				<button type="submit" className={btn('primary', 'lg', 'w-full')} disabled={busy || !password}>Open Lightbench</button>
			</form>
		</main>
	)
}
