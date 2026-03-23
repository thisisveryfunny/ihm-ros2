/**
 * Speed-related types.
 * Mirrors ROS2 geometry_msgs/Twist structure.
 */

export interface SpeedReading {
    timestamp: number;
    linearX: number; // m/s forward
    linearY: number; // m/s lateral
    angularZ: number; // rad/s yaw rate
    magnitude: number; // computed: sqrt(linearX² + linearY²)
}

export interface SpeedStats {
    current: number;
    max: number;
    min: number;
    average: number;
}
