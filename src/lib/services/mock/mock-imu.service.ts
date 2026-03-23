/**
 * Mock IMU data service.
 * Simulates accelerometer, gyroscope, and orientation readings.
 * Acceleration Z stays ~9.81 m/s² (gravity). Others add Gaussian noise.
 */

import type { ImuDataService } from '../data-service.js';
import type { ImuReading, Vector3, EulerAngles, Quaternion } from '$lib/types/imu.js';

const INTERVAL_MS = 100; // 10 Hz — typical IMU rate

function gaussian(): number {
    // Box–Muller transform for Gaussian noise
    const u1 = Math.random();
    const u2 = Math.random();
    return Math.sqrt(-2 * Math.log(u1)) * Math.cos(2 * Math.PI * u2);
}

function eulerToQuaternion(roll: number, pitch: number, yaw: number): Quaternion {
    const cr = Math.cos(roll / 2);
    const sr = Math.sin(roll / 2);
    const cp = Math.cos(pitch / 2);
    const sp = Math.sin(pitch / 2);
    const cy = Math.cos(yaw / 2);
    const sy = Math.sin(yaw / 2);
    return {
        w: cr * cp * cy + sr * sp * sy,
        x: sr * cp * cy - cr * sp * sy,
        y: cr * sp * cy + sr * cp * sy,
        z: cr * cp * sy - sr * sp * cy,
    };
}

export class MockImuService implements ImuDataService {
    readonly #callbacks = new Set<(r: ImuReading) => void>();
    #intervalId: ReturnType<typeof setInterval> | null = null;
    isConnected = false;

    // State for continuous orientation simulation
    #roll = 0;
    #pitch = 0;
    #yaw = 0;
    #gyroX = 0;
    #gyroY = 0;
    #gyroZ = 0;

    start(): void {
        if (this.#intervalId !== null) return;
        this.isConnected = true;
        this.#intervalId = setInterval(() => {
            const reading = this.#generateReading();
            this.#callbacks.forEach((cb) => cb(reading));
        }, INTERVAL_MS);
    }

    stop(): void {
        if (this.#intervalId === null) return;
        clearInterval(this.#intervalId);
        this.#intervalId = null;
        this.isConnected = false;
    }

    onReading(cb: (r: ImuReading) => void): () => void {
        this.#callbacks.add(cb);
        return () => this.#callbacks.delete(cb);
    }

    #generateReading(): ImuReading {
        const dt = INTERVAL_MS / 1000;

        // Smooth gyro with noise
        this.#gyroX += (Math.random() - 0.5) * 0.005;
        this.#gyroY += (Math.random() - 0.5) * 0.005;
        this.#gyroZ += (Math.random() - 0.5) * 0.003;

        // Damping — gyro drifts back toward 0
        this.#gyroX *= 0.98;
        this.#gyroY *= 0.98;
        this.#gyroZ *= 0.99;

        // Integrate orientation
        this.#roll += this.#gyroX * dt;
        this.#pitch += this.#gyroY * dt;
        this.#yaw += this.#gyroZ * dt;

        // Keep orientation bounded for a realistic demo
        this.#roll = Math.max(-0.3, Math.min(0.3, this.#roll));
        this.#pitch = Math.max(-0.3, Math.min(0.3, this.#pitch));

        const acceleration: Vector3 = {
            x: gaussian() * 0.05 + this.#gyroY * 0.5,
            y: gaussian() * 0.05 + this.#gyroX * 0.5,
            z: 9.81 + gaussian() * 0.08,
        };

        const gyroscope: Vector3 = {
            x: this.#gyroX + gaussian() * 0.002,
            y: this.#gyroY + gaussian() * 0.002,
            z: this.#gyroZ + gaussian() * 0.001,
        };

        const orientation: EulerAngles = {
            roll: this.#roll,
            pitch: this.#pitch,
            yaw: this.#yaw,
        };

        return {
            timestamp: Date.now(),
            acceleration,
            gyroscope,
            orientation,
            orientationQuaternion: eulerToQuaternion(this.#roll, this.#pitch, this.#yaw),
        };
    }
}
