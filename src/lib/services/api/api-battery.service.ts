/**
 * Real battery data service.
 * Polls GET /api/batterie every 2s and emits new readings.
 */

import type { BatteryDataService } from '../data-service.js';
import type { BatteryReading } from '$lib/types/battery.js';

const POLL_INTERVAL_MS = 2000;

interface BatterieRow {
	id: number;
	percentage: number;
	createdAt: string;
}

/** Approximate 7S LiPo voltage from percentage (22V empty – 29.4V full). */
function estimateVoltage(percentage: number): number {
	return 22 + (percentage / 100) * 7.4;
}

export class ApiBatteryService implements BatteryDataService {
	readonly #callbacks = new Set<(r: BatteryReading) => void>();
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

	onReading(cb: (r: BatteryReading) => void): () => void {
		this.#callbacks.add(cb);
		return () => this.#callbacks.delete(cb);
	}

	async #poll(): Promise<void> {
		if (this.#polling) return;
		this.#polling = true;

		try {
			const res = await fetch(`${import.meta.env.VITE_API_URL ?? ''}/api/batterie`);
			if (!res.ok) throw new Error(`HTTP ${res.status}`);
			const rows: BatterieRow[] = await res.json();
			this.isConnected = true;

			const newRows = rows.filter((r) => r.id > this.#lastSeenId);
			if (newRows.length === 0) return;

			this.#lastSeenId = Math.max(...newRows.map((r) => r.id));

			newRows.sort((a, b) => a.id - b.id);
			for (const row of newRows) {
				const reading: BatteryReading = {
					timestamp: Date.parse(row.createdAt),
					percentage: row.percentage,
					voltage: estimateVoltage(row.percentage),
					current: 0,
					temperature: 0,
					status: 'discharging',
					estimatedRemainingMinutes: null
				};
				this.#callbacks.forEach((cb) => cb(reading));
			}
		} catch (err) {
			console.warn('[ApiBatteryService] poll failed:', err);
			this.isConnected = false;
		} finally {
			this.#polling = false;
		}
	}
}
