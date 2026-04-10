/**
 * Real IMU data service.
 * Polls GET /api/imu every 2s and emits new readings.
 *
 * Orientation (euler + quaternion) is not available from the raw sensor POST
 * and defaults to identity. A client-side Madgwick filter could be added later
 * using the accel/gyro data to compute orientation.
 */

import type { ImuDataService } from '../data-service.js';
import type { ImuReading } from '$lib/types/imu.js';

const POLL_INTERVAL_MS = 2000;

interface ImuRow {
	id: number;
	accelX: number;
	accelY: number;
	accelZ: number;
	gyroX: number;
	gyroY: number;
	gyroZ: number;
	createdAt: string;
}

export class ApiImuService implements ImuDataService {
	readonly #callbacks = new Set<(r: ImuReading) => void>();
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

	onReading(cb: (r: ImuReading) => void): () => void {
		this.#callbacks.add(cb);
		return () => this.#callbacks.delete(cb);
	}

	async #poll(): Promise<void> {
		if (this.#polling) return;
		this.#polling = true;

		try {
			const res = await fetch('/api/imu');
			if (!res.ok) throw new Error(`HTTP ${res.status}`);
			const rows: ImuRow[] = await res.json();
			this.isConnected = true;

			const newRows = rows.filter((r) => r.id > this.#lastSeenId);
			if (newRows.length === 0) return;

			this.#lastSeenId = Math.max(...newRows.map((r) => r.id));

			newRows.sort((a, b) => a.id - b.id);
			for (const row of newRows) {
				const reading: ImuReading = {
					timestamp: Date.parse(row.createdAt),
					acceleration: { x: row.accelX, y: row.accelY, z: row.accelZ },
					gyroscope: { x: row.gyroX, y: row.gyroY, z: row.gyroZ },
					orientation: { roll: 0, pitch: 0, yaw: 0 },
					orientationQuaternion: { x: 0, y: 0, z: 0, w: 1 }
				};
				this.#callbacks.forEach((cb) => cb(reading));
			}
		} catch (err) {
			console.warn('[ApiImuService] poll failed:', err);
			this.isConnected = false;
		} finally {
			this.#polling = false;
		}
	}
}
