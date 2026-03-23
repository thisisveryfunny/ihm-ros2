/**
 * Svelte 5 runes-based speed store.
 * Uses the getter pattern to keep $state private and prevent external mutation.
 */

import type { SpeedReading, SpeedStats } from '$lib/types/speed.js';
import { addToRingBuffer } from '$lib/utils/ring-buffer.js';

const MAX_HISTORY = 120; // 60s at 2Hz (500ms interval)

function computeStats(history: SpeedReading[]): SpeedStats {
    if (history.length === 0) {
        return { current: 0, max: 0, min: 0, average: 0 };
    }
    const magnitudes = history.map((r) => r.magnitude);
    const current = magnitudes[magnitudes.length - 1];
    const max = Math.max(...magnitudes);
    const min = Math.min(...magnitudes);
    const average = magnitudes.reduce((a, b) => a + b, 0) / magnitudes.length;
    return { current, max, min, average };
}

function createSpeedStore() {
    let current = $state<SpeedReading | null>(null);
    let history = $state<SpeedReading[]>([]);
    let stats = $state<SpeedStats>({ current: 0, max: 0, min: 0, average: 0 });

    function push(reading: SpeedReading): void {
        current = reading;
        history = addToRingBuffer(history, reading, MAX_HISTORY);
        stats = computeStats(history);
    }

    function reset(): void {
        current = null;
        history = [];
        stats = { current: 0, max: 0, min: 0, average: 0 };
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

export const speedStore = createSpeedStore();
