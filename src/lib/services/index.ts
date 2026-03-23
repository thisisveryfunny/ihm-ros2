/**
 * Service factory.
 * Exports singleton service instances.
 * To switch to real ROS2 data: set VITE_USE_MOCK=false and implement ROS2 service classes.
 */

import { MockSpeedService } from './mock/mock-speed.service.js';
import { MockImuService } from './mock/mock-imu.service.js';
import { MockBatteryService } from './mock/mock-battery.service.js';

const USE_MOCK = import.meta.env.VITE_USE_MOCK !== 'false';

export const speedService = USE_MOCK
    ? new MockSpeedService()
    : new MockSpeedService(); // TODO: replace with ROS2SpeedService

export const imuService = USE_MOCK
    ? new MockImuService()
    : new MockImuService(); // TODO: replace with ROS2ImuService

export const batteryService = USE_MOCK
    ? new MockBatteryService()
    : new MockBatteryService(); // TODO: replace with ROS2BatteryService
