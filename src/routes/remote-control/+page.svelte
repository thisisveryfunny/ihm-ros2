<script lang="ts">
	import { onMount, onDestroy } from 'svelte';
	import { remoteControlClient, cameraControlClient } from '$lib/services/index.js';
	import { remoteControlStore } from '$lib/stores/remote-control.svelte.js';
	import MovementPad from '$lib/components/remote/MovementPad.svelte';
	import CameraPad from '$lib/components/remote/CameraPad.svelte';
	import CameraFeed from '$lib/components/remote/CameraFeed.svelte';
	import ConnectionPanel from '$lib/components/remote/ConnectionPanel.svelte';
	import type { Direction } from '$lib/types/remote-control.js';
	import type { CameraDirection } from '$lib/types/camera-control.js';

	let cameraReady = $state(false);
	const unsubs: Array<() => void> = [];
	const pressedMovementKeys = new Set<string>();
	const pressedCameraKeys = new Set<string>();

	const KEY_TO_DIRECTION: Record<string, Direction> = {
		w: 'front',
		W: 'front',
		s: 'back',
		S: 'back',
		a: 'left',
		A: 'left',
		d: 'right',
		D: 'right',
	};

	const KEY_TO_CAMERA: Record<string, CameraDirection> = {
		ArrowUp: 'up',
		ArrowDown: 'down',
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
		unsubs.push(
			cameraControlClient.onError((msg) => remoteControlStore.setError(`Camera: ${msg}`)),
		);
		remoteControlClient.start();
		cameraControlClient.start();
	});

	onDestroy(() => {
		unsubs.forEach((fn) => fn());
		remoteControlClient.stop();
		cameraControlClient.stop();
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

	function handleCameraStart(direction: CameraDirection) {
		remoteControlStore.setActiveCameraDirection(direction);
		cameraControlClient.sendCameraCommand(direction);
	}

	function handleCameraEnd() {
		remoteControlStore.setActiveCameraDirection(null);
		cameraControlClient.sendCameraCommand('stop');
	}

	function handleKeyDown(event: KeyboardEvent) {
		if (event.repeat) return;

		const movement = KEY_TO_DIRECTION[event.key];
		if (movement) {
			event.preventDefault();
			pressedMovementKeys.add(event.key);
			handleDirectionStart(movement);
			return;
		}

		const camera = KEY_TO_CAMERA[event.key];
		if (camera) {
			event.preventDefault();
			pressedCameraKeys.add(event.key);
			handleCameraStart(camera);
		}
	}

	function handleKeyUp(event: KeyboardEvent) {
		if (event.key in KEY_TO_DIRECTION) {
			event.preventDefault();
			pressedMovementKeys.delete(event.key);
			const remaining = [...pressedMovementKeys];
			if (remaining.length > 0) {
				handleDirectionStart(KEY_TO_DIRECTION[remaining[remaining.length - 1]]);
			} else {
				handleDirectionEnd();
			}
			return;
		}

		if (event.key in KEY_TO_CAMERA) {
			event.preventDefault();
			pressedCameraKeys.delete(event.key);
			const remaining = [...pressedCameraKeys];
			if (remaining.length > 0) {
				handleCameraStart(KEY_TO_CAMERA[remaining[remaining.length - 1]]);
			} else {
				handleCameraEnd();
			}
		}
	}

	function handleBlur() {
		pressedMovementKeys.clear();
		pressedCameraKeys.clear();
		if (remoteControlStore.activeDirection) {
			handleDirectionEnd();
		}
		handleCameraEnd();
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

		<!-- Control pads (1/3) — hidden until camera ready -->
		{#if cameraReady}
			<div class="flex flex-col items-center justify-center gap-4">
				<MovementPad
					activeDirection={remoteControlStore.activeDirection}
					disabled={remoteControlStore.connectionStatus !== 'connected'}
					onDirectionStart={handleDirectionStart}
					onDirectionEnd={handleDirectionEnd}
				/>
				<CameraPad
					activeDirection={remoteControlStore.activeCameraDirection}
					disabled={remoteControlStore.connectionStatus !== 'connected'}
					onDirectionStart={handleCameraStart}
					onDirectionEnd={handleCameraEnd}
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
					<kbd class="rounded bg-surface-700 px-1.5 py-0.5 font-mono text-slate-300">W</kbd>
					<kbd class="rounded bg-surface-700 px-1.5 py-0.5 font-mono text-slate-300">A</kbd>
					<kbd class="rounded bg-surface-700 px-1.5 py-0.5 font-mono text-slate-300">S</kbd>
					<kbd class="rounded bg-surface-700 px-1.5 py-0.5 font-mono text-slate-300">D</kbd>
					pour deplacer le robot,
					<kbd class="rounded bg-surface-700 px-1.5 py-0.5 font-mono text-slate-300">fleches</kbd>
					pour orienter la camera. Le mouvement s'arrete automatiquement au relachement.
				</p>
			</div>
		</div>
	</div>
</div>
