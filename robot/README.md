# Robot Nodes (Yahboom MicroROS-Pi5)

Python ROS2 nodes that run on the robot and communicate with the IHM web server.

## Prerequisites

- ROS2 Humble (installed on the Yahboom Pi5)
- Python 3.10+

## Installation

```sh
cd robot/
pip install -r requirements.txt
```

ROS2 message packages (`rclpy`, `sensor_msgs`, `geometry_msgs`, `nav_msgs`, `std_msgs`) are provided by the ROS2 installation — they are not pip-installed.

## Nodes

### 1. Telemetry Node

Subscribes to sensor topics and POSTs data to the web server API every 2 seconds.

```sh
# Source ROS2 first
source /opt/ros/humble/setup.bash

python3 telemetry_node.py
# Or with custom server URL:
python3 telemetry_node.py --ros-args -p server_url:=http://192.168.1.100:5173
```

**ROS2 topics subscribed:**

| Topic | Message Type | API Endpoint |
|---|---|---|
| `/imu/data` | `sensor_msgs/msg/Imu` | `POST /api/imu` |
| `/imu/mag` | `sensor_msgs/msg/MagneticField` | merged into `/api/imu` |
| `/battery` | `std_msgs/msg/Float32` | `POST /api/batterie` |
| `/odom/unfiltered` | `nav_msgs/msg/Odometry` | `POST /api/vitesse` |

**Parameters:**
- `server_url` (string, default `http://localhost:5173`)

### 2. Control Node

Connects to the WebSocket and translates movement commands to `/cmd_vel`.

```sh
source /opt/ros/humble/setup.bash

python3 control_node.py
# Or with custom settings:
python3 control_node.py --ros-args \
  -p server_url:=192.168.1.100:5173 \
  -p linear_speed:=0.3 \
  -p angular_speed:=1.5
```

**Direction mapping:**

| Command | Twist |
|---|---|
| `front` | linear.x = +linear_speed |
| `back` | linear.x = -linear_speed |
| `left` | angular.z = +angular_speed |
| `right` | angular.z = -angular_speed |
| `stop` | all zeros |

**Parameters:**
- `server_url` (string, default `localhost:5173`)
- `linear_speed` (double, default `0.2` m/s)
- `angular_speed` (double, default `1.0` rad/s)

### 3. Camera Node

Streams the Pi camera via WebRTC through the signaling WebSocket.

```sh
python3 camera_node.py
# Or with environment variables:
SERVER_URL=192.168.1.100:5173 FPS=60 python3 camera_node.py
```

This node does **not** use ROS2 — it captures directly from `/dev/video0` via OpenCV for lowest latency.

**Environment variables:**

| Variable | Default | Description |
|---|---|---|
| `SERVER_URL` | `localhost:5173` | WebSocket server host |
| `CAMERA_INDEX` | `0` | V4L2 camera device index |
| `FRAME_WIDTH` | `640` | Capture width |
| `FRAME_HEIGHT` | `480` | Capture height |
| `FPS` | `30` | Target framerate |

**WebRTC signaling flow:**
1. Camera node connects to `ws://SERVER_URL/ws?role=robot`
2. Browser sends a `webrtc-offer` (relayed by server)
3. Camera node responds with `webrtc-answer`
4. ICE candidates are exchanged
5. Video streams directly from robot to browser over UDP

### 4. Collision Detection Node

Reads lidar data and stops the robot if an obstacle is closer than the threshold. Sends an alert to the dashboard via WebSocket and publishes `/collision_blocked` so the control node ignores movement commands until the obstacle clears.

```sh
source /opt/ros/humble/setup.bash

python3 collision_node.py
# Or with custom threshold:
python3 collision_node.py --ros-args \
  -p server_url:=localhost:5173 \
  -p min_distance:=0.5
```

**ROS2 topics:**

| Topic | Type | Direction | Description |
|---|---|---|---|
| `/scan` | `sensor_msgs/msg/LaserScan` | Subscribe | Lidar data from MS200 |
| `/cmd_vel` | `geometry_msgs/msg/Twist` | Publish | Sends stop (all zeros) on collision |
| `/collision_blocked` | `std_msgs/msg/Bool` | Publish | True when blocked, consumed by control_node |

**Parameters:**
- `server_url` (string, default `localhost:5173`)
- `min_distance` (double, default `0.3` meters)

**WebSocket message sent to dashboard:**
```json
{ "type": "collision-alert", "distance": 0.15, "blocked": true }
{ "type": "collision-alert", "distance": 0.45, "blocked": false }
```

Messages are only sent on state transitions (blocked→clear or clear→blocked) to avoid flooding.

**Interaction with control_node:** The control node subscribes to `/collision_blocked`. When `true`, all movement commands from the dashboard are ignored — the user must release the key and press again once the obstacle clears.

### 5. Sign Detection Node

Uses the camera and ORB feature matching to detect printed signs (from `assets/` folder) and control the robot. Dashboard commands override sign detection when keys are pressed.

```sh
source /opt/ros/humble/setup.bash

python3 sign_detection_node.py
# Or with custom settings:
python3 sign_detection_node.py --ros-args \
  -p server_url:=localhost:5173 \
  -p assets_path:=../assets \
  -p match_threshold:=20 \
  -p linear_speed:=0.2
```

**Sign → Action mapping:**

| Sign | File | Action |
|---|---|---|
| Stop | `assets/stop-sign.jpg` | speed = 0 |
| Up arrow | `assets/up-arrow.jpg` | forward |
| Down arrow | `assets/down-arrow.jpg` | backward |
| Left arrow | `assets/left-arrow.jpg` | turn left |
| Right arrow | `assets/right-arrow.jpg` | turn right |
| None detected | — | no command (dashboard control passes through) |

**Parameters:**
- `server_url` (string, default `localhost:5173`)
- `assets_path` (string, default `../assets`)
- `linear_speed` (double, default `0.2` m/s)
- `angular_speed` (double, default `1.0` rad/s)
- `match_threshold` (int, default `15`) — minimum ORB matches to trigger
- `process_interval` (double, default `0.1` s) — time between frame processing
- `camera_index` (int, default `0`)

**WebSocket message sent to dashboard:**
```json
{ "type": "sign-detected", "sign": "stop" }
{ "type": "sign-detected", "sign": null }
```

Messages are sent only on state transitions (new sign detected or sign lost).

**Note:** This node shares the camera with `camera_node.py`. If both need to run simultaneously, use different `camera_index` values or a shared camera feed.

## Testing Without the Robot

You can simulate sensor data with `ros2 topic pub`:

```sh
# Simulate battery at 75%
ros2 topic pub /battery std_msgs/msg/Float32 "{data: 75.0}" --once

# Simulate IMU
ros2 topic pub /imu/data sensor_msgs/msg/Imu "{linear_acceleration: {x: 0.1, y: 0.2, z: 9.8}, angular_velocity: {x: 0.01, y: -0.02, z: 0.0}}" --once

# Verify control node output
ros2 topic echo /cmd_vel

# Simulate lidar with close obstacle (triggers collision)
ros2 topic pub /scan sensor_msgs/msg/LaserScan "{ranges: [0.2, 0.3, 5.0], range_min: 0.05, range_max: 12.0}" --once

# Simulate lidar with clear path
ros2 topic pub /scan sensor_msgs/msg/LaserScan "{ranges: [2.0, 3.0, 5.0], range_min: 0.05, range_max: 12.0}" --once

# Check collision state
ros2 topic echo /collision_blocked
```
