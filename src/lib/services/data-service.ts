/**
 * Abstract service interfaces for robot data.
 * Mock implementations live in ./mock/.
 * Future ROS2 WebSocket implementations will live in ./ros2/.
 *
 * The `onReading` callback pattern returns an unsubscribe function,
 * enabling clean teardown in Svelte onDestroy hooks.
 */

import type { SpeedReading } from '$lib/types/speed.js';
import type { ImuReading } from '$lib/types/imu.js';
import type { BatteryReading } from '$lib/types/battery.js';

export interface DataService {
    start(): void;
    stop(): void;
    readonly isConnected: boolean;
}

export interface SpeedDataService extends DataService {
    onReading(cb: (reading: SpeedReading) => void): () => void;
}

export interface ImuDataService extends DataService {
    onReading(cb: (reading: ImuReading) => void): () => void;
}

export interface BatteryDataService extends DataService {
    onReading(cb: (reading: BatteryReading) => void): () => void;
}
