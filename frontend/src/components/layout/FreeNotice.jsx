// slim strip shown at the top of every page, including the login page
export function FreeNotice() {
	return (
		<div className="bg-ink px-4 py-2 text-center text-xs leading-5 text-bg sm:text-sm">
			Lightbench is free and not for sale. If you paid for it, you got scammed.{' '}
			<a href="https://github.com/S-Alif/lightbench" target="_blank" rel="noopener noreferrer" className="font-semibold underline underline-offset-2 hover:opacity-80">
				github.com/S-Alif/lightbench
			</a>
		</div>
	)
}
