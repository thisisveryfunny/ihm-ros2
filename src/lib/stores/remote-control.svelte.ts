/**
 * Svelte 5 runes-based store for remote control state.
 * Snapshot state (not time-series), so uses discrete setters instead of push().
 */

import type { ConnectionStatus, Direction } from '$lib/types/remote-control.js';
import type { CameraDirection } from '$lib/types/camera-control.js';

function createRemoteControlStore() {
	let connectionStatus = $state<ConnectionStatus>('disconnected');
	let connectedRobots = $state(0);
	let activeDirection = $state<Direction | null>(null);
	let activeCameraDirection = $state<CameraDirection | null>(null);
	let lastError = $state<string | null>(null);
	let latencyMs = $state<number | null>(null);
	let collisionBlocked = $state(false);
	let collisionDistance = $state<number | null>(null);

	function reset(): void {
		connectionStatus = 'disconnected';
		connectedRobots = 0;
		activeDirection = null;
		activeCameraDirection = null;
		lastError = null;
		latencyMs = null;
		collisionBlocked = false;
		collisionDistance = null;
	}

	return {
		get connectionStatus() {
			return connectionStatus;
		},
		get connectedRobots() {
			return connectedRobots;
		},
		get activeDirection() {
			return activeDirection;
		},
		get activeCameraDirection() {
			return activeCameraDirection;
		},
		get lastError() {
			return lastError;
		},
		get latencyMs() {
			return latencyMs;
		},
		get collisionBlocked() {
			return collisionBlocked;
		},
		get collisionDistance() {
			return collisionDistance;
		},

		setConnectionStatus(status: ConnectionStatus) {
			connectionStatus = status;
		},
		setConnectedRobots(count: number) {
			connectedRobots = count;
		},
		setActiveDirection(dir: Direction | null) {
			activeDirection = dir;
		},
		setActiveCameraDirection(dir: CameraDirection | null) {
			activeCameraDirection = dir;
		},
		setError(msg: string | null) {
			lastError = msg;
		},
		setLatency(ms: number | null) {
			latencyMs = ms;
		},
		setCollision(blocked: boolean, distance: number | null) {
			collisionBlocked = blocked;
			collisionDistance = distance;
		},

		reset,
	};
}

export const remoteControlStore = createRemoteControlStore();
