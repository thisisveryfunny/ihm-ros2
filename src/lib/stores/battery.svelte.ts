/**
 * Svelte 5 runes-based battery store.
 */

import type { BatteryReading, BatteryStats } from '$lib/types/battery.js';
import { addToRingBuffer } from '$lib/utils/ring-buffer.js';

const MAX_HISTORY = 150; // ~5 min at 0.5Hz

function computeStats(current: BatteryReading, history: BatteryReading[]): BatteryStats {
    let trend: BatteryStats['trend'] = 'stable';
    if (history.length >= 5) {
        const recent = history.slice(-5).map((r) => r.percentage);
        const delta = recent[recent.length - 1] - recent[0];
        if (delta > 0.2) trend = 'rising';
        else if (delta < -0.2) trend = 'falling';
    }
    return {
        current: current.percentage,
        voltage: current.voltage,
        status: current.status,
        trend,
    };
}

function createBatteryStore() {
    let current = $state<BatteryReading | null>(null);
    let history = $state<BatteryReading[]>([]);
    let stats = $state<BatteryStats | null>(null);

    function push(reading: BatteryReading): void {
        current = reading;
        history = addToRingBuffer(history, reading, MAX_HISTORY);
        stats = computeStats(reading, history);
    }

    function reset(): void {
        current = null;
        history = [];
        stats = null;
    }

    return {
        get current() {
            return current;
        },
        get history() {
            return history;
        },
        get stats() {
            return stats;
        },
        push,
        reset,
    };
}

export const batteryStore = createBatteryStore();
