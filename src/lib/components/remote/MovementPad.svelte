<script lang="ts">
	import type { Direction } from '$lib/types/remote-control.js';

	interface Props {
		activeDirection: Direction | null;
		disabled?: boolean;
		onDirectionStart: (direction: Direction) => void;
		onDirectionEnd: () => void;
	}

	let { activeDirection, disabled = false, onDirectionStart, onDirectionEnd }: Props = $props();

	type KeyButton = {
		direction: Direction;
		label: string;
		letter: string;
		row: string;
		col: string;
	};

	const keys: KeyButton[] = [
		{ direction: 'front', label: 'Avancer', letter: 'W', row: 'row-start-1', col: 'col-start-2' },
		{ direction: 'left', label: 'Gauche', letter: 'A', row: 'row-start-2', col: 'col-start-1' },
		{ direction: 'back', label: 'Reculer', letter: 'S', row: 'row-start-2', col: 'col-start-2' },
		{ direction: 'right', label: 'Droite', letter: 'D', row: 'row-start-2', col: 'col-start-3' },
	];

	function isActive(direction: Direction): boolean {
		return activeDirection === direction;
	}
</script>

<div class="rounded-xl border border-surface-700 bg-surface-800 p-6">
	<p class="mb-4 text-center text-xs font-medium uppercase tracking-wider text-slate-500">
		Deplacement
	</p>

	<!-- svelte-ignore a11y_no_static_element_interactions -->
	<div class="grid grid-cols-3 grid-rows-2 gap-2" style="touch-action: none;">
		{#each keys as key}
			<button
				class="{key.row} {key.col} flex h-16 w-16 items-center justify-center rounded-xl border
					font-mono text-xl font-bold
					transition-all duration-100 select-none
					{isActive(key.direction)
					? 'border-accent-500 bg-accent-500/20 text-accent-400'
					: 'border-surface-600 bg-surface-700 text-slate-400 hover:bg-surface-600 hover:text-slate-200'}
					{disabled ? 'cursor-not-allowed opacity-40' : 'cursor-pointer active:scale-95'}"
				aria-label={key.label}
				{disabled}
				onpointerdown={() => {
					if (!disabled) onDirectionStart(key.direction);
				}}
				onpointerup={() => {
					if (!disabled) onDirectionEnd();
				}}
				onpointerleave={() => {
					if (!disabled && isActive(key.direction)) onDirectionEnd();
				}}
			>
				{key.letter}
			</button>
		{/each}
	</div>

	<p class="mt-4 text-center text-xs text-slate-600">Clavier : W A S D</p>
</div>
