/**
 * Shared types for ROS2 message envelopes and time-series data.
 * These mirror standard ROS2 message structures for future WebSocket integration.
 */

export interface RosHeader {
    stamp: number; // Unix ms timestamp
    frameId: string;
}

export interface RosMessage<T> {
    header: RosHeader;
    data: T;
}

/** A single value at a point in time — used as ECharts data point */
export interface TimePoint {
    timestamp: number; // Unix ms
    value: number;
}

/** A named time series for multi-line charts */
export interface TimeSeries {
    name: string;
    points: TimePoint[];
}
