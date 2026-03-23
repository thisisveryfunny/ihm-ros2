/**
 * Svelte 5 runes-based IMU store.
 * Stores last N readings for each sensor axis.
 */

import type { ImuReading } from '$lib/types/imu.js';
import { addToRingBuffer } from '$lib/utils/ring-buffer.js';

const MAX_HISTORY = 200; // 20s at 10Hz

function createImuStore() {
    let current = $state<ImuReading | null>(null);
    let history = $state<ImuReading[]>([]);

    function push(reading: ImuReading): void {
        current = reading;
        history = addToRingBuffer(history, reading, MAX_HISTORY);
    }

    function reset(): void {
        current = null;
        history = [];
    }

    return {
        get current() {
            return current;
        },
        get history() {
            return history;
        },
        push,
        reset,
    };
}

export const imuStore = createImuStore();
