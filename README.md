# IHM ROS2

Real-time web dashboard and control system for a Yahboom MicroROS-Pi5 robot. Streams telemetry (battery, speed, IMU), provides remote movement control, live camera via WebRTC, collision avoidance, and AI-based sign detection.

## Architecture Overview

```
+-------------------------------+          +-------------------------------+
|        ROBOT (Pi5)            |          |      WEB SERVER (Node.js)     |
|                               |          |                               |
|  telemetry_node.py ----HTTP POST-------> |  /api/batterie                |
|    /imu/data, /battery,       |          |  /api/vitesse    -> PostgreSQL|
|    /odom, /imu/mag            |          |  /api/imu                     |
|                               |          |                               |
|  control_node.py <---WS cmd------------ |  /ws (WebSocket server)       |
|    -> /cmd_vel                |          |    |                          |
|                               |          |    | relay                    |
|  collision_node.py            |          |    |                          |
|    /scan -> /cmd_vel (stop)   |          |                               |
|    -> /collision_blocked      |          +-------------------------------+
|    ----WS collision-alert---> |                    ^     |
|                               |                    |     |
|  camera_node.py               |                    |     v
|    /dev/video0 --WebRTC-------|----------->   +------------------+
|    (peer-to-peer UDP video)   |               |    DASHBOARD     |
|                               |               |    (Browser)     |
|  sign_detection_node.py       |               |                  |
|    /dev/video0 -> ORB match   |               |  - Telemetry     |
|    -> /cmd_vel                |               |  - Controls      |
|    ----WS sign-detected-----> |               |  - Video feed    |
|                               |               |  - Alerts        |
+-------------------------------+               +------------------+
```

## Project Structure

```
ihm-ros2/
├── src/                          # SvelteKit web app
│   ├── lib/server/
│   │   ├── db/                   # Drizzle ORM (schema + connection)
│   │   └── ws/                   # WebSocket server (protocol + relay)
│   └── routes/api/               # REST endpoints (batterie, vitesse, imu)
├── robot/                        # Python ROS2 nodes (run on the robot)
│   ├── telemetry_node.py         # Sensor data -> HTTP POST
│   ├── control_node.py           # WS commands -> /cmd_vel
│   ├── collision_node.py         # Lidar -> collision avoidance
│   ├── camera_node.py            # Camera -> WebRTC stream
│   └── sign_detection_node.py    # Camera -> sign detection -> /cmd_vel
├── assets/                       # Reference images for sign detection
├── db/                           # Docker Compose + init.sql for PostgreSQL
├── server.js                     # Production server (HTTP + WebSocket)
└── vite.config.ts                # Dev server with WebSocket plugin
```

---

## Data Flow Diagrams

### 1. Telemetry Flow (every 2 seconds)

```
   ROBOT                              SERVER                         DATABASE
   -----                              ------                         --------
   /imu/data ─┐
   /imu/mag  ─┤
   /battery  ─┼─> telemetry_node ──HTTP POST──> /api/batterie ──> batterie table
   /odom     ─┘                                 /api/vitesse  ──> vitesse table
                                                /api/imu      ──> imu table
```

The telemetry node caches the latest reading from each ROS2 topic and sends all three POST requests in a background thread every 2 seconds.

### 2. Movement Control Flow

```
   DASHBOARD                    SERVER                      ROBOT
   ---------                    ------                      -----
   User presses key
        |
        v
   { type: "command",      WS relay to
     direction: "front" } ──────────────> control_node
        |                                     |
        |                                     v
        |                               /cmd_vel (Twist)
        |                                     |
   User releases key                          v
        |                                  MOTORS
        v
   { type: "command",
     direction: "stop" } ───────────────> control_node
                                              |
                                              v
                                         /cmd_vel = 0
```

### 3. Collision Detection Flow

```
   ROBOT                                SERVER                   DASHBOARD
   -----                                ------                   ---------
   /scan (lidar)
       |
       v
   collision_node
       |
       ├── obstacle < 0.3m?
       |       |
       |    YES |
       |       v
       |   /cmd_vel = STOP
       |   /collision_blocked = true
       |   WS { collision-alert, ───────> relay ──────> Alert shown
       |        blocked: true }                         (user must
       |                                                 re-press key)
       |    NO (cleared)
       |       v
       |   /collision_blocked = false
       |   WS { collision-alert, ───────> relay ──────> Alert cleared
       |        blocked: false }
       |
       v
   control_node checks /collision_blocked
       |
       ├── blocked = true?  -> ignore movement commands
       └── blocked = false? -> pass commands to /cmd_vel
```

### 4. WebRTC Camera Stream Flow

```
   DASHBOARD                    SERVER (signaling)              ROBOT
   ---------                    ------------------              -----
   Create RTCPeerConnection
        |
        v
   { webrtc-offer, sdp } ────> relay ─────────────> camera_node
                                                         |
                                                    Open /dev/video0
                                                    Create RTCPeerConnection
                                                    Add video track
                                                         |
                                                         v
   camera_node answer   <────── relay <──────── { webrtc-answer, sdp }
        |
        v
   ICE candidates  <─────────> relay <──────────> ICE candidates
        |                                              |
        v                                              v
   ╔═══════════════════════════════════════════════════════╗
   ║        Direct peer-to-peer UDP video stream           ║
   ║        (640x480, 30-60fps, H.264/VP8)                 ║
   ╚═══════════════════════════════════════════════════════╝
```

Once the WebRTC connection is established, video flows directly between browser and robot. The server is only used for the initial signaling handshake.

### 5. Sign Detection Flow

```
   ROBOT                                SERVER              DASHBOARD
   -----                                ------              ---------
   /dev/video0 (camera)
       |
       v
   sign_detection_node
       |
   ORB feature matching
   vs reference images:
   ┌─────────────────────┐
   │ stop-sign.jpg       │
   │ up-arrow.jpg        │
   │ down-arrow.jpg      │
   │ left-arrow.jpg      │
   │ right-arrow.jpg     │
   └─────────────────────┘
       |
       ├── Match found (>= 15 good matches)?
       |       |
       |    YES |
       |       v
       |   /cmd_vel = corresponding direction
       |   WS { sign-detected, ─────> relay ──────> Sign indicator
       |        sign: "up" }                        shown on UI
       |
       |    NO (no sign)
       |       v
       |   Nothing published
       |   WS { sign-detected, ─────> relay ──────> Indicator cleared
       |        sign: null }
       |
       v
   Dashboard commands OVERRIDE sign detection
   (higher publish frequency to /cmd_vel)
```

### 6. Control Priority

Multiple nodes can publish to `/cmd_vel`. Priority is determined by publish frequency:

```
   Priority (highest to lowest):
   ┌─────────────────────────────────────────────────┐
   │ 1. collision_node     Immediate stop on obstacle │
   │    (overrides everything when blocked)           │
   │                                                  │
   │ 2. control_node       Dashboard keypresses       │
   │    (publishes on every key event)                │
   │                                                  │
   │ 3. sign_detection_node  Sign-based commands      │
   │    (publishes every 0.1s when sign detected)     │
   └─────────────────────────────────────────────────┘
```

- **Collision** has absolute priority: stops the robot and blocks `control_node` via `/collision_blocked`
- **Dashboard** overrides sign detection because keypresses generate commands more frequently
- **Sign detection** acts as a fallback when no keys are pressed

---

## WebSocket Protocol

All communication goes through a single WebSocket at `/ws`.

### Connection

| Role | URL | Purpose |
|---|---|---|
| Robot | `ws://host/ws?role=robot` | Receive commands, send alerts |
| Controller | `ws://host/ws?role=controller` | Send commands, receive alerts |

### Message Types

| Message | Direction | Description |
|---|---|---|
| `command` | Controller -> Robots | Movement: front/back/left/right/stop |
| `status` | Server -> Controllers | Robot connection count |
| `collision-alert` | Robot -> Controllers | Obstacle detected/cleared |
| `sign-detected` | Robot -> Controllers | Sign recognized (or null) |
| `webrtc-offer` | Controller -> Robot | WebRTC SDP offer |
| `webrtc-answer` | Robot -> Controller | WebRTC SDP answer |
| `webrtc-ice` | Bidirectional | WebRTC ICE candidate |
| `ping` / `pong` | Bidirectional | Heartbeat |
| `error` | Server -> Client | Invalid message notification |

### Message Formats

```json
{ "type": "command", "direction": "front" }
{ "type": "status", "connectedRobots": 1 }
{ "type": "collision-alert", "distance": 0.15, "blocked": true }
{ "type": "sign-detected", "sign": "stop" }
{ "type": "sign-detected", "sign": null }
{ "type": "webrtc-offer", "sdp": "<SDP>" }
{ "type": "webrtc-answer", "sdp": "<SDP>" }
{ "type": "webrtc-ice", "candidate": "<candidate>", "sdpMid": "0", "sdpMLineIndex": 0 }
```

---

## REST API

| Method | Endpoint | Request Body | Response |
|---|---|---|---|
| POST | `/api/batterie` | `{ "percentage": 85.5 }` | 201 + created row |
| GET | `/api/batterie` | — | All readings (newest first) |
| POST | `/api/vitesse` | `{ "speed": 1.23 }` | 201 + created row |
| GET | `/api/vitesse` | — | All readings (newest first) |
| POST | `/api/imu` | `{ "accel_x", ..., "mag_z" }` | 201 + created row |
| GET | `/api/imu` | — | All readings (newest first) |

All records include auto-generated `id` and `createdAt` (timestamptz).

---

## Database Schema

```sql
batterie (id SERIAL PK, percentage REAL, created_at TIMESTAMPTZ)
vitesse  (id SERIAL PK, speed REAL, created_at TIMESTAMPTZ)
imu      (id SERIAL PK, accel_x/y/z REAL, gyro_x/y/z REAL, mag_x/y/z REAL, created_at TIMESTAMPTZ)
```

---

## Setup

### Prerequisites

- Node.js 18+
- Docker & Docker Compose
- (Robot) ROS2 Humble, Python 3.10+

### Web Server

```sh
npm install

# Start database
npm run db:start

# Create .env
echo "DATABASE_URL=postgresql://ros2:ros2@localhost:5436/ros2" > .env

# Push schema
npm run db:push

# Development
npm run dev

# Production
npm run build
npm start    # Runs server.js on port 3000
```

### Robot Nodes

```sh
cd robot/
pip install -r requirements.txt
source /opt/ros/humble/setup.bash

# Run all nodes (in separate terminals)
python3 telemetry_node.py
python3 control_node.py
python3 collision_node.py
python3 camera_node.py
python3 sign_detection_node.py
```

See [robot/README.md](robot/README.md) for detailed node documentation, parameters, and testing instructions.

---

## ROS2 Topics

| Topic | Type | Published By | Subscribed By |
|---|---|---|---|
| `/cmd_vel` | `geometry_msgs/Twist` | control, collision, sign_detection | Motor driver |
| `/imu/data` | `sensor_msgs/Imu` | IMU hardware | telemetry |
| `/imu/mag` | `sensor_msgs/MagneticField` | IMU hardware | telemetry |
| `/battery` | `std_msgs/Float32` | Battery monitor | telemetry |
| `/odom/unfiltered` | `nav_msgs/Odometry` | Wheel encoders | telemetry |
| `/scan` | `sensor_msgs/LaserScan` | MS200 lidar | collision |
| `/collision_blocked` | `std_msgs/Bool` | collision | control |
