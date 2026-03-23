<script lang="ts">
	import StatusBadge from '$lib/components/cards/StatusBadge.svelte';
	import type { ConnectionStatus } from '$lib/types/remote-control.js';

	interface Props {
		connectionStatus: ConnectionStatus;
		connectedRobots: number;
		latencyMs: number | null;
		lastError: string | null;
	}

	let { connectionStatus, connectedRobots, latencyMs, lastError }: Props = $props();

	const badgeStatus = $derived(connectionStatus === 'connected' ? 'connected' : 'disconnected');

	const badgeLabel = $derived(
		connectionStatus === 'connecting'
			? 'Connexion...'
			: connectionStatus === 'error'
				? 'Erreur'
				: undefined,
	);
</script>

<div class="flex flex-wrap items-center gap-3">
	<StatusBadge status={badgeStatus} label={badgeLabel} />

	{#if connectionStatus === 'connected'}
		<span class="text-xs text-slate-500">
			{connectedRobots} robot{connectedRobots !== 1 ? 's' : ''}
		</span>
	{/if}

	{#if latencyMs !== null}
		<span class="font-mono text-xs text-slate-500">{latencyMs} ms</span>
	{/if}

	{#if lastError}
		<span class="text-xs text-danger-400">{lastError}</span>
	{/if}
</div>
