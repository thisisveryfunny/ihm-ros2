/**
 * Service factory.
 * Exports singleton service instances backed by the real backend API.
 */

import { ApiSpeedService, ApiImuService, ApiBatteryService } from './api/index.js';
import { RemoteControlClient } from './remote-control-client.js';

export const speedService = new ApiSpeedService();

export const imuService = new ApiImuService();

export const batteryService = new ApiBatteryService();

export const remoteControlClient = new RemoteControlClient();
