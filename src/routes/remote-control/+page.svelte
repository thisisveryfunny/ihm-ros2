<script lang="ts">
	import { onMount, onDestroy } from 'svelte';
	import { remoteControlClient } from '$lib/services/index.js';
	import { remoteControlStore } from '$lib/stores/remote-control.svelte.js';
	import DirectionPad from '$lib/components/remote/DirectionPad.svelte';
	import CameraFeed from '$lib/components/remote/CameraFeed.svelte';
	import ConnectionPanel from '$lib/components/remote/ConnectionPanel.svelte';
	import type { Direction } from '$lib/types/remote-control.js';

	let cameraReady = $state(false);
	const unsubs: Array<() => void> = [];
	const pressedKeys = new Set<string>();

	const KEY_TO_DIRECTION: Record<string, Direction> = {
		ArrowUp: 'front',
		ArrowDown: 'back',
		ArrowLeft: 'left',
		ArrowRight: 'right',
	};

	onMount(() => {
		unsubs.push(
			remoteControlClient.onStatusChange((status, robots) => {
				remoteControlStore.setConnectionStatus(status);
				remoteControlStore.setConnectedRobots(robots);
			}),
		);
		unsubs.push(remoteControlClient.onError((msg) => remoteControlStore.setError(msg)));
		unsubs.push(remoteControlClient.onLatency((ms) => remoteControlStore.setLatency(ms)));
		remoteControlClient.start();
	});

	onDestroy(() => {
		unsubs.forEach((fn) => fn());
		remoteControlClient.stop();
		remoteControlStore.reset();
	});

	function handleDirectionStart(direction: Direction) {
		remoteControlStore.setActiveDirection(direction);
		remoteControlClient.sendCommand(direction);
	}

	function handleDirectionEnd() {
		remoteControlStore.setActiveDirection(null);
		remoteControlClient.sendCommand('stop');
	}

	function handleKeyDown(event: KeyboardEvent) {
		const direction = KEY_TO_DIRECTION[event.key];
		if (!direction || event.repeat) return;
		event.preventDefault();
		pressedKeys.add(event.key);
		handleDirectionStart(direction);
	}

	function handleKeyUp(event: KeyboardEvent) {
		if (!(event.key in KEY_TO_DIRECTION)) return;
		event.preventDefault();
		pressedKeys.delete(event.key);

		// If other arrow keys are still held, resume the most recent one
		const remaining = [...pressedKeys].filter((k) => k in KEY_TO_DIRECTION);
		if (remaining.length > 0) {
			handleDirectionStart(KEY_TO_DIRECTION[remaining[remaining.length - 1]]);
		} else {
			handleDirectionEnd();
		}
	}

	function handleBlur() {
		pressedKeys.clear();
		if (remoteControlStore.activeDirection) {
			handleDirectionEnd();
		}
	}
</script>

<svelte:window onkeydown={handleKeyDown} onkeyup={handleKeyUp} onblur={handleBlur} />

<div class="space-y-6">
	<!-- Header -->
	<div class="flex items-center justify-between">
		<div>
			<h1 class="text-xl font-bold text-slate-100">Controle a distance</h1>
			<p class="mt-1 text-sm text-slate-500">Commande directionnelle et flux camera</p>
		</div>
		<ConnectionPanel
			connectionStatus={remoteControlStore.connectionStatus}
			connectedRobots={remoteControlStore.connectedRobots}
			latencyMs={remoteControlStore.latencyMs}
			lastError={remoteControlStore.lastError}
		/>
	</div>

	<!-- Main content: camera + controls -->
	<div class="grid grid-cols-1 gap-6 lg:grid-cols-3">
		<!-- Camera feed (2/3) -->
		<div class="relative lg:col-span-2">
			{#if !cameraReady}
				<div class="absolute inset-0 z-10 flex flex-col items-center justify-center gap-4 rounded-xl border border-surface-700 bg-surface-800">
					<svg class="h-8 w-8 animate-spin text-ros-orange" viewBox="0 0 24 24" fill="none">
						<circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
						<path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"></path>
					</svg>
					<p class="text-sm text-slate-400">Connexion en cours...</p>
				</div>
			{/if}
			<CameraFeed onready={() => cameraReady = true} />
		</div>

		<!-- Control pad (1/3) — hidden until camera ready -->
		{#if cameraReady}
			<div class="flex items-center justify-center">
				<DirectionPad
					activeDirection={remoteControlStore.activeDirection}
					disabled={remoteControlStore.connectionStatus !== 'connected'}
					onDirectionStart={handleDirectionStart}
					onDirectionEnd={handleDirectionEnd}
				/>
			</div>
		{/if}
	</div>

	<!-- Info banner -->
	<div class="rounded-xl border border-ros-orange/20 bg-ros-orange/5 p-4">
		<div class="flex items-start gap-3">
			<svg
				class="mt-0.5 h-5 w-5 shrink-0 text-ros-orange"
				viewBox="0 0 24 24"
				fill="none"
				stroke="currentColor"
				stroke-width="2"
			>
				<circle cx="12" cy="12" r="10" />
				<line x1="12" y1="8" x2="12" y2="12" />
				<line x1="12" y1="16" x2="12.01" y2="16" />
			</svg>
			<div>
				<p class="text-sm font-medium text-ros-orange">Raccourcis clavier</p>
				<p class="mt-1 text-xs text-slate-500">
					Utilisez les
					<kbd class="rounded bg-surface-700 px-1.5 py-0.5 font-mono text-slate-300"
						>fleches</kbd
					>
					du clavier pour controler le robot. Le robot s'arrete automatiquement
					lorsque la touche est relachee.
				</p>
			</div>
		</div>
	</div>
</div>
