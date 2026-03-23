# Architecture Documentation

## System Components

The system is split into three main parts: the **robot** (Yahboom MicroROS-Pi5), the **web server** (Node.js/SvelteKit), and the **dashboard** (browser). They communicate over HTTP, WebSocket, and WebRTC.

```
┌─────────────────────────────────────────────────────────────────┐
│                         NETWORK (LAN)                           │
│                                                                 │
│  ┌──────────────────────┐     ┌──────────────────────────────┐  │
│  │   ROBOT (Pi5)        │     │   WEB SERVER (Node.js)       │  │
│  │                      │     │                              │  │
│  │  ┌────────────────┐  │     │  ┌────────────────────────┐  │  │
│  │  │ telemetry_node │──┼─HTTP──>│ REST API               │  │  │
│  │  └────────────────┘  │POST │  │  /api/batterie         │  │  │
│  │                      │     │  │  /api/vitesse          │  │  │
│  │  ┌────────────────┐  │     │  │  /api/imu              │  │  │
│  │  │ control_node   │<─┼─WS───>│                        │  │  │
│  │  └────────────────┘  │     │  └────────────────────────┘  │  │
│  │                      │     │                              │  │
│  │  ┌────────────────┐  │     │  ┌────────────────────────┐  │  │
│  │  │ collision_node │──┼─WS───>│ WebSocket Server (/ws) │  │  │
│  │  └────────────────┘  │     │  │  - Command relay       │  │  │
│  │                      │     │  │  - Alert broadcast     │  │  │
│  │  ┌────────────────┐  │     │  │  - WebRTC signaling    │  │  │
│  │  │ camera_node    │──┼─WS───>│                        │  │  │
│  │  └────────────────┘  │     │  └────────────────────────┘  │  │
│  │                      │     │                              │  │
│  │  ┌────────────────┐  │     │  ┌────────────────────────┐  │  │
│  │  │ sign_detection │──┼─WS───>│ PostgreSQL             │  │  │
│  │  └────────────────┘  │     │  │  batterie, vitesse,   │  │  │
│  │                      │     │  │  imu tables            │  │  │
│  └──────────────────────┘     │  └────────────────────────┘  │  │
│                               └──────────────────────────────┘  │
│                                        ^                        │
│                                        | HTTP + WS              │
│                                        v                        │
│                               ┌──────────────────┐              │
│                               │   DASHBOARD      │              │
│                               │   (Browser)      │              │
│                               │                  │              │
│                               │  - Telemetry     │              │
│                               │  - Controls      │              │
│                               │  - Video (WebRTC)│              │
│                               │  - Alerts        │              │
│                               └──────────────────┘              │
└─────────────────────────────────────────────────────────────────┘
```

---

## Robot Node Interactions

Each Python node on the robot has a specific responsibility. They communicate with each other via ROS2 topics and with the web server via HTTP or WebSocket.

```
                        ROS2 TOPIC BUS
    ┌──────────────────────────────────────────────────┐
    │                                                  │
    │  /imu/data  /battery  /odom  /scan  /cmd_vel     │
    │     │          │        │      │       ^         │
    │     │          │        │      │       │         │
    │     v          v        v      │       │         │
    │  ┌──────────────────────┐     │       │         │
    │  │   telemetry_node     │     │       │         │
    │  │   (read sensors,     │     │       │         │
    │  │    POST to API)      │     │       │         │
    │  └──────────────────────┘     │       │         │
    │                                │       │         │
    │                                v       │         │
    │                    ┌───────────────┐   │         │
    │                    │collision_node │   │         │
    │                    │ (lidar check) │───┘         │
    │                    └───────┬───────┘             │
    │                            │                     │
    │                  /collision_blocked               │
    │                            │                     │
    │                            v                     │
    │                    ┌───────────────┐             │
    │    WS commands --> │ control_node  │─────────────┤
    │                    │ (dashboard    │  /cmd_vel   │
    │                    │  commands)    │             │
    │                    └───────────────┘             │
    │                                                  │
    │                    ┌───────────────┐             │
    │                    │sign_detection │─────────────┤
    │                    │  (ORB match)  │  /cmd_vel   │
    │                    └───────────────┘             │
    │                                                  │
    │                    ┌───────────────┐             │
    │                    │ camera_node   │             │
    │                    │ (WebRTC       │             │
    │                    │  streaming)   │             │
    │                    └───────────────┘             │
    └──────────────────────────────────────────────────┘
                                │
                                v
                           MOTOR DRIVER
                         (ESP32 via MicroROS)
```

---

## WebSocket Message Routing

The WebSocket server at `/ws` routes messages based on type and sender role.

```
                    ┌──────────────────────────┐
                    │     WebSocket Server      │
                    │         (/ws)             │
                    │                          │
   CONTROLLERS      │   ┌──────────────────┐   │      ROBOTS
   (browsers)       │   │  Message Router  │   │   (ROS2 nodes)
                    │   └──────────────────┘   │
        │           │          │               │         │
        │           │          │               │         │
        ├─command──>│──────────┼──command──────>│─────────┤
        │           │          │               │         │
        │<─status───│<─────────┤               │         │
        │           │          │               │         │
        │<──────────│<─collision-alert─────────│<────────┤
        │           │          │               │         │
        │<──────────│<──sign-detected──────────│<────────┤
        │           │          │               │         │
        ├─offer────>│──────────┼──offer────────>│─────────┤
        │           │          │               │         │
        │<──────────│<─answer──┤               │<────────┤
        │           │          │               │         │
        │<──ice────>│<─────────┼──ice──────────>│<───────>│
        │           │          │               │         │
                    └──────────────────────────┘
```

**Routing rules:**
- `command` → broadcast to all robots
- `status` → sent to controllers (on robot connect/disconnect)
- `collision-alert`, `sign-detected` → broadcast to all controllers
- `webrtc-offer/answer/ice` → relay to opposite role
- `ping/pong` → handled locally per connection

---

## Data Persistence

Telemetry data flows from robot sensors to PostgreSQL via the REST API.

```
  ROS2 Sensors              telemetry_node           REST API            PostgreSQL
  ────────────              ──────────────           ────────            ──────────
  /battery ──────> cache ─┐
  /imu/data ─────> cache ─┼── every 2s ──> POST /api/batterie ──> batterie table
  /imu/mag ──────> cache ─┤                POST /api/imu      ──> imu table
  /odom ─────────> cache ─┘                POST /api/vitesse   ──> vitesse table
                                                     │
                                                     v
                                              GET endpoints
                                           (newest first, JSON)
                                                     │
                                                     v
                                               Dashboard charts
                                            (ECharts visualization)
```

**Database tables:**

```
┌──────────────────┐  ┌──────────────────┐  ┌──────────────────────────┐
│    batterie      │  │    vitesse       │  │          imu             │
├──────────────────┤  ├──────────────────┤  ├──────────────────────────┤
│ id       SERIAL  │  │ id       SERIAL  │  │ id         SERIAL       │
│ percentage REAL  │  │ speed    REAL    │  │ accel_x/y/z  REAL      │
│ created_at TSTZ  │  │ created_at TSTZ  │  │ gyro_x/y/z   REAL      │
└──────────────────┘  └──────────────────┘  │ mag_x/y/z    REAL      │
                                            │ created_at    TSTZ      │
                                            └──────────────────────────┘
```

---

## WebRTC Video Pipeline

Video flows peer-to-peer. The server is only used for the initial signaling handshake.

```
  ROBOT                                                      BROWSER
  ─────                                                      ───────

  /dev/video0 (Pi Camera)
       │
       v
  OpenCV VideoCapture
  (MJPG, 640x480, 30fps)
       │
       v
  CameraVideoTrack
  (BGR -> RGB -> VideoFrame)
       │
       v
  aiortc RTCPeerConnection          WebSocket             RTCPeerConnection
       │                          (signaling only)              │
       │──── answer SDP ──────────────>──────────────> setRemoteDescription
       │<─── offer SDP ───────────────<──────────────< createOffer
       │──── ICE candidates ──────────>──────────────> addIceCandidate
       │<─── ICE candidates ──────────<──────────────< onicecandidate
       │                                                       │
       ╚═══════════════════════════════════════════════════════╝
              Direct UDP media stream (VP8/H.264)
                    No server in the middle
```

---

## Sign Detection Pipeline

ORB (Oriented FAST and Rotated BRIEF) feature matching for lightweight, GPU-free sign recognition.

```
  STARTUP:
  ┌─────────────────────────────────────────────┐
  │  Load reference images from assets/          │
  │                                              │
  │  stop-sign.jpg ──> ORB keypoints + desc ──┐ │
  │  up-arrow.jpg ───> ORB keypoints + desc ──┤ │
  │  down-arrow.jpg ─> ORB keypoints + desc ──┤ │
  │  left-arrow.jpg ─> ORB keypoints + desc ──┤ │
  │  right-arrow.jpg > ORB keypoints + desc ──┘ │
  └─────────────────────────────────────────────┘

  EACH FRAME (every 0.1s):
  ┌─────────────────────────────────────────────┐
  │  Camera frame                                │
  │       │                                      │
  │       v                                      │
  │  Grayscale conversion                        │
  │       │                                      │
  │       v                                      │
  │  ORB feature detection (500 features)        │
  │       │                                      │
  │       v                                      │
  │  BFMatcher (Hamming distance, KNN k=2)       │
  │  vs each reference                           │
  │       │                                      │
  │       v                                      │
  │  Lowe's ratio test (0.75)                    │
  │  -> count good matches per reference         │
  │       │                                      │
  │       v                                      │
  │  Best match >= 15 good matches?              │
  │       │                                      │
  │    YES: publish /cmd_vel + WS sign-detected  │
  │    NO:  do nothing (dashboard controls)      │
  └─────────────────────────────────────────────┘
```

---

## Collision Avoidance Detail

```
  /scan (LaserScan, ~10Hz from MS200 lidar)
       │
       v
  Filter ranges:
    - Remove 0.0, inf, NaN
    - Keep range_min < r < range_max
       │
       v
  Find minimum distance
       │
       ├── min_dist < 0.3m (threshold)
       │        │
       │     ┌──v───────────────────────────┐
       │     │ BLOCKED                       │
       │     │                               │
       │     │ /cmd_vel = Twist() [all zero] │
       │     │ /collision_blocked = true     │
       │     │ WS: collision-alert, true     │
       │     │                               │
       │     │ control_node ignores commands │
       │     │ (except "stop")               │
       │     └───────────────────────────────┘
       │
       └── min_dist >= 0.3m
                │
             ┌──v───────────────────────────┐
             │ CLEAR                         │
             │                               │
             │ /collision_blocked = false     │
             │ WS: collision-alert, false    │
             │                               │
             │ control_node resumes normal   │
             │ command processing            │
             └───────────────────────────────┘

  Alerts are only sent on state TRANSITIONS
  (blocked -> clear, or clear -> blocked)
```

---

## Dev vs Production

| | Development | Production |
|---|---|---|
| Command | `npm run dev` | `npm run build && npm start` |
| HTTP Server | Vite dev server | `server.js` (Node.js) |
| WebSocket | Vite plugin hooks into dev server | Attached to HTTP server in `server.js` |
| WS Port | 5173 (same as dev server) | 3000 (configurable via `PORT`) |
| Hot Reload | Yes (Vite HMR) | No |
| SvelteKit | Dev middleware | Built handler from `./build/handler.js` |

Both modes serve the WebSocket at the `/ws` path on the same port as the HTTP server.
