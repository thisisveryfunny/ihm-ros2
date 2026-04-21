/**
 * WebSocket client for robot remote control.
 * Connects as a "controller" role and sends directional commands.
 * Receives status updates (connected robots) and pong (latency).
 * Auto-reconnects with exponential backoff.
 */

import type { Direction, ClientMessage, ConnectionStatus } from '$lib/types/remote-control.js';
import { parseServerMessage } from '$lib/types/remote-control.js';

type StatusCallback = (status: ConnectionStatus, connectedRobots: number) => void;
type ErrorCallback = (message: string) => void;
type LatencyCallback = (ms: number) => void;
type CollisionCallback = (payload: { distance: number; blocked: boolean }) => void;

const PING_INTERVAL_MS = 10_000;
const INITIAL_RECONNECT_DELAY_MS = 1_000;
const MAX_RECONNECT_DELAY_MS = 30_000;

export class RemoteControlClient {
	#ws: WebSocket | null = null;
	#statusCallbacks = new Set<StatusCallback>();
	#errorCallbacks = new Set<ErrorCallback>();
	#latencyCallbacks = new Set<LatencyCallback>();
	#collisionCallbacks = new Set<CollisionCallback>();
	#reconnectTimer: ReturnType<typeof setTimeout> | null = null;
	#pingTimer: ReturnType<typeof setInterval> | null = null;
	#pingStart = 0;
	#reconnectDelay = INITIAL_RECONNECT_DELAY_MS;
	#stopped = true;
	#connectedRobots = 0;

	isConnected = false;

	start(): void {
		this.#stopped = false;
		this.#connect();
	}

	stop(): void {
		this.#stopped = true;
		this.#clearTimers();
		if (this.#ws) {
			this.#ws.close();
			this.#ws = null;
		}
		this.isConnected = false;
		this.#notifyStatus('disconnected');
	}

	sendCommand(direction: Direction): void {
		this.#send({ type: 'command', direction });
	}

	onStatusChange(cb: StatusCallback): () => void {
		this.#statusCallbacks.add(cb);
		return () => this.#statusCallbacks.delete(cb);
	}

	onError(cb: ErrorCallback): () => void {
		this.#errorCallbacks.add(cb);
		return () => this.#errorCallbacks.delete(cb);
	}

	onLatency(cb: LatencyCallback): () => void {
		this.#latencyCallbacks.add(cb);
		return () => this.#latencyCallbacks.delete(cb);
	}

	onCollisionAlert(cb: CollisionCallback): () => void {
		this.#collisionCallbacks.add(cb);
		return () => this.#collisionCallbacks.delete(cb);
	}

	#connect(): void {
		if (this.#stopped) return;

		this.#notifyStatus('connecting');

		const wsUrl = import.meta.env.VITE_WS_URL;
		const url = wsUrl
			? `${wsUrl}/ws?role=controller`
			: `${location.protocol === 'https:' ? 'wss:' : 'ws:'}//${location.host}/ws?role=controller`;

		const ws = new WebSocket(url);
		this.#ws = ws;

		ws.addEventListener('open', () => {
			this.isConnected = true;
			this.#reconnectDelay = INITIAL_RECONNECT_DELAY_MS;
			this.#notifyStatus('connected');
			this.#startPing();
		});

		ws.addEventListener('close', () => {
			this.isConnected = false;
			this.#stopPing();
			if (!this.#stopped) {
				this.#notifyStatus('disconnected');
				this.#scheduleReconnect();
			}
		});

		ws.addEventListener('error', () => {
			this.#notifyError('Erreur de connexion WebSocket');
		});

		ws.addEventListener('message', (event) => {
			const msg = parseServerMessage(String(event.data));
			if (!msg) return;

			switch (msg.type) {
				case 'status':
					this.#connectedRobots = msg.connectedRobots;
					this.#notifyStatus('connected');
					break;
				case 'pong':
					if (this.#pingStart > 0) {
						this.#latencyCallbacks.forEach((cb) => cb(Date.now() - this.#pingStart));
						this.#pingStart = 0;
					}
					break;
				case 'error':
					this.#notifyError(msg.message);
					break;
				case 'collision-alert':
					this.#collisionCallbacks.forEach((cb) =>
						cb({ distance: msg.distance, blocked: msg.blocked })
					);
					break;
			}
		});
	}

	#send(msg: ClientMessage): void {
		if (this.#ws?.readyState === WebSocket.OPEN) {
			this.#ws.send(JSON.stringify(msg));
		}
	}

	#startPing(): void {
		this.#stopPing();
		this.#pingTimer = setInterval(() => {
			this.#pingStart = Date.now();
			this.#send({ type: 'ping' });
		}, PING_INTERVAL_MS);
	}

	#stopPing(): void {
		if (this.#pingTimer !== null) {
			clearInterval(this.#pingTimer);
			this.#pingTimer = null;
		}
	}

	#scheduleReconnect(): void {
		if (this.#stopped) return;
		this.#reconnectTimer = setTimeout(() => {
			this.#reconnectTimer = null;
			this.#connect();
		}, this.#reconnectDelay);
		this.#reconnectDelay = Math.min(this.#reconnectDelay * 2, MAX_RECONNECT_DELAY_MS);
	}

	#clearTimers(): void {
		this.#stopPing();
		if (this.#reconnectTimer !== null) {
			clearTimeout(this.#reconnectTimer);
			this.#reconnectTimer = null;
		}
	}

	#notifyStatus(status: ConnectionStatus): void {
		this.#statusCallbacks.forEach((cb) => cb(status, this.#connectedRobots));
	}

	#notifyError(message: string): void {
		this.#errorCallbacks.forEach((cb) => cb(message));
	}
}
