/**
 * Number formatting utilities for the robot dashboard.
 */

export function formatSpeed(ms: number): string {
    return `${ms.toFixed(2)} m/s`;
}

export function formatAngleDeg(rad: number): string {
    return `${(rad * (180 / Math.PI)).toFixed(1)}°`;
}

export function formatAngleRad(rad: number): string {
    return `${rad.toFixed(3)} rad`;
}

export function formatPercent(value: number): string {
    return `${value.toFixed(0)}%`;
}

export function formatVoltage(v: number): string {
    return `${v.toFixed(2)} V`;
}

export function formatCurrent(a: number): string {
    return `${a.toFixed(2)} A`;
}

export function formatTemperature(c: number): string {
    return `${c.toFixed(1)} °C`;
}

export function formatAcceleration(ms2: number): string {
    return `${ms2.toFixed(3)} m/s²`;
}

export function formatAngularRate(rads: number): string {
    return `${rads.toFixed(3)} rad/s`;
}

export function formatDuration(minutes: number): string {
    if (minutes < 60) return `${Math.round(minutes)} min`;
    const h = Math.floor(minutes / 60);
    const m = Math.round(minutes % 60);
    return `${h}h ${m}m`;
}

export function formatTimestamp(ms: number): string {
    return new Date(ms).toLocaleTimeString();
}
