<script lang="ts">
	import type { Direction } from '$lib/types/remote-control.js';

	interface Props {
		activeDirection: Direction | null;
		disabled?: boolean;
		onDirectionStart: (direction: Direction) => void;
		onDirectionEnd: () => void;
	}

	let { activeDirection, disabled = false, onDirectionStart, onDirectionEnd }: Props = $props();

	type ArrowButton = {
		direction: Direction;
		label: string;
		row: string;
		col: string;
		path: string;
	};

	const arrows: ArrowButton[] = [
		{
			direction: 'front',
			label: 'Avancer',
			row: 'row-start-1',
			col: 'col-start-2',
			path: 'M18 15l-6-6-6 6',
		},
		{
			direction: 'left',
			label: 'Gauche',
			row: 'row-start-2',
			col: 'col-start-1',
			path: 'M15 18l-6-6 6-6',
		},
		{
			direction: 'right',
			label: 'Droite',
			row: 'row-start-2',
			col: 'col-start-3',
			path: 'M9 18l6-6-6-6',
		},
		{
			direction: 'back',
			label: 'Reculer',
			row: 'row-start-3',
			col: 'col-start-2',
			path: 'M6 9l6 6 6-6',
		},
	];

	function isActive(direction: Direction): boolean {
		return activeDirection === direction;
	}
</script>

<div class="rounded-xl border border-surface-700 bg-surface-800 p-6">
	<p class="mb-4 text-center text-xs font-medium uppercase tracking-wider text-slate-500">
		Commandes
	</p>

	<!-- svelte-ignore a11y_no_static_element_interactions -->
	<div class="grid grid-cols-3 grid-rows-3 gap-2" style="touch-action: none;">
		{#each arrows as arrow}
			<button
				class="{arrow.row} {arrow.col} flex h-16 w-16 items-center justify-center rounded-xl border
					transition-all duration-100 select-none
					{isActive(arrow.direction)
					? 'border-accent-500 bg-accent-500/20 text-accent-400'
					: 'border-surface-600 bg-surface-700 text-slate-400 hover:bg-surface-600 hover:text-slate-200'}
					{disabled ? 'cursor-not-allowed opacity-40' : 'cursor-pointer active:scale-95'}"
				aria-label={arrow.label}
				{disabled}
				onpointerdown={() => {
					if (!disabled) onDirectionStart(arrow.direction);
				}}
				onpointerup={() => {
					if (!disabled) onDirectionEnd();
				}}
				onpointerleave={() => {
					if (!disabled && isActive(arrow.direction)) onDirectionEnd();
				}}
			>
				<svg
					class="h-7 w-7"
					viewBox="0 0 24 24"
					fill="none"
					stroke="currentColor"
					stroke-width="2.5"
					stroke-linecap="round"
					stroke-linejoin="round"
				>
					<path d={arrow.path} />
				</svg>
			</button>
		{/each}

		<!-- Center stop button -->
		<button
			class="col-start-2 row-start-2 flex h-16 w-16 items-center justify-center rounded-xl border
				transition-all duration-100 select-none cursor-pointer
				border-surface-600 bg-surface-700 text-slate-400
				hover:border-danger-500 hover:bg-danger-500/20 hover:text-danger-400
				active:scale-95
				{disabled ? 'cursor-not-allowed opacity-40' : ''}"
			aria-label="Arreter"
			{disabled}
			onclick={() => {
				if (!disabled) {
					onDirectionStart('stop');
					onDirectionEnd();
				}
			}}
		>
			<span class="text-xs font-bold uppercase">Arrêt</span>
		</button>
	</div>

	<p class="mt-4 text-center text-xs text-slate-600">
		Clavier : touches flechees
	</p>
</div>
