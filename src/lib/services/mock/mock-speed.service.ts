/**
 * Mock speed data service.
 * Simulates robot velocity using a random walk in [0, 2.0 m/s].
 * Replace with ROS2WebSocketSpeedService for real data.
 */

import type { SpeedDataService } from '../data-service.js';
import type { SpeedReading } from '$lib/types/speed.js';

const INTERVAL_MS = 500;

export class MockSpeedService implements SpeedDataService {
    readonly #callbacks = new Set<(r: SpeedReading) => void>();
    #intervalId: ReturnType<typeof setInterval> | null = null;
    #currentSpeed = 0.5;
    #angularZ = 0;
    isConnected = false;

    start(): void {
        if (this.#intervalId !== null) return;
        this.isConnected = true;
        this.#intervalId = setInterval(() => {
            const reading = this.#generateReading();
            this.#callbacks.forEach((cb) => cb(reading));
        }, INTERVAL_MS);
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

    #generateReading(): SpeedReading {
        // Random walk with damping toward 0.5 m/s baseline
        const delta = (Math.random() - 0.48) * 0.12;
        this.#currentSpeed = Math.max(0, Math.min(2.0, this.#currentSpeed + delta));

        // Smooth angular rate
        this.#angularZ += (Math.random() - 0.5) * 0.08;
        this.#angularZ = Math.max(-0.5, Math.min(0.5, this.#angularZ));

        return {
            timestamp: Date.now(),
            linearX: this.#currentSpeed,
            linearY: 0,
            angularZ: this.#angularZ,
            magnitude: this.#currentSpeed,
        };
    }
}
