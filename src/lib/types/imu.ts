/**
 * IMU (Inertial Measurement Unit) types.
 * Mirrors ROS2 sensor_msgs/Imu structure.
 */

export interface Vector3 {
    x: number;
    y: number;
    z: number;
}

export interface Quaternion {
    x: number;
    y: number;
    z: number;
    w: number;
}

export interface EulerAngles {
    roll: number; // rad — rotation around X
    pitch: number; // rad — rotation around Y
    yaw: number; // rad — rotation around Z
}

export interface ImuReading {
    timestamp: number;
    acceleration: Vector3; // m/s²
    gyroscope: Vector3; // rad/s
    orientation: EulerAngles;
    orientationQuaternion: Quaternion;
}
