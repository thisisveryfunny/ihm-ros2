/**
 * Real speed data service.
 * Polls GET /api/vitesse every 2s and emits new readings.
 */

import type { SpeedDataService } from '../data-service.js';
import type { SpeedReading } from '$lib/types/speed.js';

const POLL_INTERVAL_MS = 2000;

interface VitesseRow {
	id: number;
	speed: number;
	createdAt: string;
}

export class ApiSpeedService implements SpeedDataService {
	readonly #callbacks = new Set<(r: SpeedReading) => void>();
	#intervalId: ReturnType<typeof setInterval> | null = null;
	#lastSeenId = 0;
	#polling = false;
	isConnected = false;

	start(): void {
		if (this.#intervalId !== null) return;
		this.#poll();
		this.#intervalId = setInterval(() => this.#poll(), POLL_INTERVAL_MS);
	}

	stop(): void {
		if (this.#intervalId === null) return;
		clearInterval(this.#intervalId);
		this.#intervalId = null;
		this.isConnected = false;
	}

	onReading(cb: (r: SpeedReading) => void): () => void {
		this.#callbacks.add(cb);
		return () => this.#callbacks.delete(cb);
	}

	async #poll(): Promise<void> {
		if (this.#polling) return;
		this.#polling = true;

		try {
			const res = await fetch('/api/vitesse');
			if (!res.ok) throw new Error(`HTTP ${res.status}`);
			const rows: VitesseRow[] = await res.json();
			this.isConnected = true;

			const newRows = rows.filter((r) => r.id > this.#lastSeenId);
			if (newRows.length === 0) return;

			this.#lastSeenId = Math.max(...newRows.map((r) => r.id));

			newRows.sort((a, b) => a.id - b.id);
			for (const row of newRows) {
				const reading: SpeedReading = {
					timestamp: Date.parse(row.createdAt),
					linearX: row.speed,
					linearY: 0,
					angularZ: 0,
					magnitude: row.speed
				};
				this.#callbacks.forEach((cb) => cb(reading));
			}
		} catch (err) {
			console.warn('[ApiSpeedService] poll failed:', err);
			this.isConnected = false;
		} finally {
			this.#polling = false;
		}
	}
}
