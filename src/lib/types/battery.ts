/**
 * Battery-related types.
 * Mirrors ROS2 sensor_msgs/BatteryState structure.
 */

export type BatteryStatus = 'charging' | 'discharging' | 'full' | 'unknown';

export interface BatteryReading {
    timestamp: number;
    percentage: number; // 0–100
    voltage: number; // Volts (2S battery: ~6.0V-8.4V)
    current: number; // Amperes (positive = charging, negative = discharging)
    temperature: number; // Celsius
    status: BatteryStatus;
    estimatedRemainingMinutes: number | null; // null when charging
}

export interface BatteryStats {
    current: number; // percentage
    voltage: number;
    status: BatteryStatus;
    trend: 'rising' | 'falling' | 'stable';
}
