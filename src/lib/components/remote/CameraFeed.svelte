<script lang="ts">
	interface Props {
		streamUrl?: string | null;
		alt?: string;
	}

	let { streamUrl = null, alt = 'Flux camera du robot' }: Props = $props();

	let hasError = $state(false);

	function handleError() {
		hasError = true;
	}

	// Reset error state when URL changes
	$effect(() => {
		if (streamUrl) hasError = false;
	});
</script>

<div
	class="relative aspect-video overflow-hidden rounded-xl border border-surface-700 bg-surface-900"
>
	{#if streamUrl && !hasError}
		<img
			src={streamUrl}
			{alt}
			class="h-full w-full object-contain"
			onerror={handleError}
		/>
	{:else if streamUrl && hasError}
		<!-- Error fallback -->
		<div class="flex h-full w-full flex-col items-center justify-center gap-3">
			<svg
				class="h-12 w-12 text-danger-400"
				viewBox="0 0 24 24"
				fill="none"
				stroke="currentColor"
				stroke-width="1.5"
			>
				<path
					d="M15.182 15.182a4.5 4.5 0 0 1-6.364 0M21 12a9 9 0 1 1-18 0 9 9 0 0 1 18 0zM9.75 9.75c0 .414-.168.75-.375.75S9 10.164 9 9.75 9.168 9 9.375 9s.375.336.375.75zm-.375 0h.008v.015h-.008V9.75zm5.625 0c0 .414-.168.75-.375.75s-.375-.336-.375-.75.168-.75.375-.75.375.336.375.75zm-.375 0h.008v.015h-.008V9.75z"
				/>
			</svg>
			<p class="text-sm text-danger-400">Flux indisponible</p>
			<p class="text-xs text-slate-500">Impossible de charger le flux camera</p>
		</div>
	{:else}
		<!-- Mock placeholder -->
		<div class="flex h-full w-full flex-col items-center justify-center gap-4">
			<div class="rounded-2xl bg-surface-800 p-6">
				<svg
					class="h-16 w-16 text-slate-600"
					viewBox="0 0 24 24"
					fill="none"
					stroke="currentColor"
					stroke-width="1.5"
				>
					<path
						d="m15.75 10.5 4.72-4.72a.75.75 0 0 1 1.28.53v11.38a.75.75 0 0 1-1.28.53l-4.72-4.72M4.5 18.75h9a2.25 2.25 0 0 0 2.25-2.25v-9a2.25 2.25 0 0 0-2.25-2.25h-9A2.25 2.25 0 0 0 2.25 7.5v9a2.25 2.25 0 0 0 2.25 2.25z"
					/>
				</svg>
			</div>
			<div class="text-center">
				<p class="text-sm font-medium text-slate-400">Flux camera</p>
				<p class="mt-1 text-xs text-slate-500">En attente du flux camera...</p>
			</div>
			<div class="flex items-center gap-2">
				<span class="h-2 w-2 animate-pulse rounded-full bg-slate-600"></span>
				<span class="text-xs text-slate-600">Mode simulation</span>
			</div>
		</div>
	{/if}
</div>
