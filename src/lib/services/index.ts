/**
 * Service factory.
 * Exports singleton service instances.
 * Set VITE_USE_MOCK=false to use real API-polling services instead of mocks.
 */

import { MockSpeedService } from './mock/mock-speed.service.js';
import { MockImuService } from './mock/mock-imu.service.js';
import { MockBatteryService } from './mock/mock-battery.service.js';
import { ApiSpeedService, ApiImuService, ApiBatteryService } from './api/index.js';
import { RemoteControlClient } from './remote-control-client.js';

const USE_MOCK = import.meta.env.VITE_USE_MOCK !== 'false';

export const speedService = USE_MOCK ? new MockSpeedService() : new ApiSpeedService();

export const imuService = USE_MOCK ? new MockImuService() : new ApiImuService();

export const batteryService = USE_MOCK ? new MockBatteryService() : new ApiBatteryService();

export const remoteControlClient = new RemoteControlClient();
