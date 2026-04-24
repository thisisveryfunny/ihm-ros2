<script lang="ts">
	import type { CameraDirection } from '$lib/types/camera-control.js';

	interface Props {
		activeDirection: CameraDirection | null;
		disabled?: boolean;
		onDirectionStart: (direction: CameraDirection) => void;
		onDirectionEnd: () => void;
	}

	let { activeDirection, disabled = false, onDirectionStart, onDirectionEnd }: Props = $props();

	type ArrowButton = {
		direction: CameraDirection;
		label: string;
		row: string;
		col: string;
		path: string;
	};

	const arrows: ArrowButton[] = [
		{
			direction: 'up',
			label: 'Haut',
			row: 'row-start-1',
			col: 'col-start-2',
			path: 'M18 15l-6-6-6 6'
		},
		{
			direction: 'left',
			label: 'Gauche',
			row: 'row-start-2',
			col: 'col-start-1',
			path: 'M15 18l-6-6 6-6'
		},
		{
			direction: 'right',
			label: 'Droite',
			row: 'row-start-2',
			col: 'col-start-3',
			path: 'M9 18l6-6-6-6'
		},
		{
			direction: 'down',
			label: 'Bas',
			row: 'row-start-3',
			col: 'col-start-2',
			path: 'M6 9l6 6 6-6'
		}
	];

	function isActive(direction: CameraDirection): boolean {
		return activeDirection === direction;
	}
</script>

<div class="rounded-xl border border-surface-700 bg-surface-800 p-6">
	<p class="mb-4 text-center text-xs font-medium tracking-wider text-slate-500 uppercase">Camera</p>

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
	</div>

	<p class="mt-4 text-center text-xs text-slate-600">Clavier : flèches</p>
</div>
