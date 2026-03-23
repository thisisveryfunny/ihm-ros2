/**
 * Mock battery data service.
 * Simulates slow discharge (7S LiPo: 22V–29.4V range).
 * Occasionally simulates a brief charging event.
 */

import type { BatteryDataService } from '../data-service.js';
import type { BatteryReading, BatteryStatus } from '$lib/types/battery.js';

const INTERVAL_MS = 2000; // 0.5 Hz — battery changes slowly

// 7S LiPo voltage curve approximation
function percentageToVoltage(pct: number): number {
    return 22 + (pct / 100) * 7.4;
}

export class MockBatteryService implements BatteryDataService {
    readonly #callbacks = new Set<(r: BatteryReading) => void>();
    #intervalId: ReturnType<typeof setInterval> | null = null;
    isConnected = false;

    #percentage = 75;
    #isCharging = false;
    #chargeCyclesLeft = 0;
    #tickCount = 0;

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

    onReading(cb: (r: BatteryReading) => void): () => void {
        this.#callbacks.add(cb);
        return () => this.#callbacks.delete(cb);
    }

    #generateReading(): BatteryReading {
        this.#tickCount++;

        // Simulate occasional charging (every ~90s)
        if (!this.#isCharging && this.#tickCount % 45 === 0 && this.#percentage < 90) {
            this.#isCharging = true;
            this.#chargeCyclesLeft = 15; // charge for ~30s
        }
        if (this.#isCharging) {
            this.#chargeCyclesLeft--;
            if (this.#chargeCyclesLeft <= 0) this.#isCharging = false;
        }

        // Discharge: -0.05% per tick (~2.5%/min). Charging: +0.2% per tick.
        if (this.#isCharging) {
            this.#percentage = Math.min(100, this.#percentage + 0.2);
        } else {
            this.#percentage = Math.max(0, this.#percentage - 0.05 + (Math.random() - 0.5) * 0.02);
        }

        const voltage = percentageToVoltage(this.#percentage) + (Math.random() - 0.5) * 0.05;
        const current = this.#isCharging
            ? 2.5 + Math.random() * 0.3 // charging current
            : -(1.5 + Math.random() * 0.5); // discharging current

        let status: BatteryStatus;
        if (this.#percentage >= 99) status = 'full';
        else if (this.#isCharging) status = 'charging';
        else status = 'discharging';

        const remainingMinutes =
            status === 'discharging'
                ? (this.#percentage / 2.5) * 60 // rough estimate
                : null;

        return {
            timestamp: Date.now(),
            percentage: Math.round(this.#percentage * 10) / 10,
            voltage: Math.round(voltage * 100) / 100,
            current: Math.round(current * 100) / 100,
            temperature: 28 + Math.random() * 4,
            status,
            estimatedRemainingMinutes: remainingMinutes,
        };
    }
}
