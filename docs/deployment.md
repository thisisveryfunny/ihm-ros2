# Production Deployment on the Robot (Pi5 + ngrok)

Everything runs on the Yahboom MicroROS-Pi5: PostgreSQL, the Node.js web server, all ROS2 nodes, and ngrok for external access.

## Architecture (Production)

```
┌─────────────────────────── Pi5 (robot) ───────────────────────────┐
│                                                                    │
│  ┌──────────────┐   ┌──────────────────────────────────────────┐  │
│  │  PostgreSQL   │   │  Node.js (server.js)                     │  │
│  │  (Docker)     │   │                                          │  │
│  │  port 5436    │<──│  SvelteKit app   + WebSocket (/ws)       │  │
│  └──────────────┘   │  port 3000                                │  │
│                      └──────────────────┬───────────────────────┘  │
│                                         │                          │
│                                    ┌────┴─────┐                    │
│                                    │  ngrok   │                    │
│                                    │  :3000   │                    │
│                                    └────┬─────┘                    │
│                                         │                          │
│  ┌──────────────────────────────────────┼────────────────────────┐ │
│  │  ROS2 Nodes (all connect to localhost:3000)                   │ │
│  │  telemetry_node  control_node  collision_node                 │ │
│  │  camera_node     sign_detection_node                          │ │
│  └───────────────────────────────────────────────────────────────┘ │
└────────────────────────────────────────────────────────────────────┘
                              │
                         ngrok tunnel
                              │
                              v
                    https://xxxx.ngrok-free.app
                              │
                              v
                    ┌──────────────────┐
                    │   Browser        │
                    │   (anywhere)     │
                    └──────────────────┘
```

---

## Step-by-Step Setup

### 1. Install prerequisites on the Pi5

```sh
# Node.js (via nvm)
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.40.1/install.sh | bash
source ~/.bashrc
nvm install 20
nvm use 20

# Docker (for PostgreSQL)
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER
# Log out and back in for group change to take effect

# ngrok
curl -sSL https://ngrok-agent.s3.amazonaws.com/ngrok-v3-stable-linux-arm64.tgz \
  | sudo tar xz -C /usr/local/bin
```

### 2. Clone and build the project

```sh
cd ~
git clone <your-repo-url> ihm-ros2
cd ihm-ros2
npm install
npm run build
```

### 3. Configure environment

```sh
# .env file (already in .gitignore)
cat > .env << 'EOF'
DATABASE_URL=postgresql://ros2:ros2@localhost:5436/ros2
PORT=3000
HOST=0.0.0.0
EOF
```

### 4. Start the database

```sh
npm run db:start
# Wait for health check to pass:
docker exec ros2-yaboom-ihm pg_isready -U ros2 -d ros2
```

On first start, `db/init.sql` runs automatically and creates the tables.

### 5. Push Drizzle schema (first time only)

```sh
npm run db:push
```

### 6. Start the web server

```sh
npm start
# Output: Server with WebSocket listening on 0.0.0.0:3000
```

Verify locally:
```sh
curl http://localhost:3000/api/batterie
# Should return [] (empty array)
```

### 7. Set up ngrok

```sh
# One-time: authenticate (get your token at https://dashboard.ngrok.com)
ngrok config add-authtoken <YOUR_AUTHTOKEN>

# Start the tunnel
ngrok http 3000
```

ngrok will display a public URL like:
```
Forwarding   https://abcd-1234.ngrok-free.app -> http://localhost:3000
```

Open that URL in a browser from anywhere — you'll see the dashboard.

### 8. Start ROS2 nodes

Open separate terminals (or use `tmux`/`screen`):

```sh
source /opt/ros/humble/setup.bash
cd ~/ihm-ros2/robot

# All nodes connect to localhost since everything is on the Pi5
python3 telemetry_node.py &
python3 control_node.py &
python3 collision_node.py &
python3 camera_node.py &
python3 sign_detection_node.py &
```

Default `server_url` is `localhost:5173` for some nodes — override to `localhost:3000` for production:

```sh
python3 telemetry_node.py --ros-args -p server_url:=http://localhost:3000 &
python3 control_node.py --ros-args -p server_url:=localhost:3000 &
python3 collision_node.py --ros-args -p server_url:=localhost:3000 &
SERVER_URL=localhost:3000 python3 camera_node.py &
python3 sign_detection_node.py --ros-args -p server_url:=localhost:3000 &
```

---

## WebRTC Note (Important)

WebRTC video streaming through ngrok has a caveat. WebRTC tries to establish a **direct UDP peer-to-peer** connection. When the browser is on a different network than the robot:

- The WebRTC signaling (offer/answer/ICE) works fine through ngrok (it's just WebSocket messages)
- But the actual video stream needs a TURN server to relay media when direct UDP fails

**Without a TURN server**, WebRTC will only work if:
- The browser is on the same LAN as the robot, OR
- The robot has a public IP (unlikely behind NAT)

**To fix this**, add a TURN server configuration to `camera_node.py` when creating the RTCPeerConnection:

```python
pc = RTCPeerConnection(configuration=RTCConfiguration(
    iceServers=[
        RTCIceServer(urls="stun:stun.l.google.com:19302"),
        RTCIceServer(
            urls="turn:your-turn-server:3478",
            username="user",
            credential="password",
        ),
    ]
))
```

Free TURN options:
- [Open Relay (metered.ca)](https://www.metered.ca/tools/openrelay/) — free TURN server
- Self-hosted [coturn](https://github.com/coturn/coturn)

If you only need dashboard access from the same LAN, this is not an issue.

---

## Running Everything at Boot (systemd)

To have services start automatically when the Pi5 boots:

### Web server service

```sh
sudo tee /etc/systemd/system/ihm-web.service << 'EOF'
[Unit]
Description=IHM ROS2 Web Server
After=docker.service
Requires=docker.service

[Service]
Type=simple
User=pi
WorkingDirectory=/home/pi/ihm-ros2
ExecStartPre=/usr/bin/docker compose -f db/docker-compose.yml up -d
ExecStart=/home/pi/.nvm/versions/node/v20/bin/node server.js
EnvironmentFile=/home/pi/ihm-ros2/.env
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF
```

### ngrok service

```sh
sudo tee /etc/systemd/system/ihm-ngrok.service << 'EOF'
[Unit]
Description=ngrok tunnel for IHM dashboard
After=ihm-web.service

[Service]
Type=simple
User=pi
ExecStart=/usr/local/bin/ngrok http 3000
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF
```

### ROS2 nodes service

```sh
sudo tee /etc/systemd/system/ihm-ros2-nodes.service << 'EOF'
[Unit]
Description=IHM ROS2 Robot Nodes
After=ihm-web.service

[Service]
Type=simple
User=pi
WorkingDirectory=/home/pi/ihm-ros2/robot
ExecStart=/bin/bash -c '\
  source /opt/ros/humble/setup.bash && \
  python3 telemetry_node.py --ros-args -p server_url:=http://localhost:3000 & \
  python3 control_node.py --ros-args -p server_url:=localhost:3000 & \
  python3 collision_node.py --ros-args -p server_url:=localhost:3000 & \
  SERVER_URL=localhost:3000 python3 camera_node.py & \
  python3 sign_detection_node.py --ros-args -p server_url:=localhost:3000 & \
  wait'
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF
```

### Enable and start

```sh
sudo systemctl daemon-reload
sudo systemctl enable ihm-web ihm-ngrok ihm-ros2-nodes
sudo systemctl start ihm-web ihm-ngrok ihm-ros2-nodes

# Check status
sudo systemctl status ihm-web ihm-ngrok ihm-ros2-nodes

# View logs
journalctl -u ihm-web -f
journalctl -u ihm-ngrok -f
journalctl -u ihm-ros2-nodes -f
```

---

## ngrok with a Fixed Subdomain (Optional)

Free ngrok gives you a random URL each restart. To get a stable URL:

1. Get a free static domain at [ngrok dashboard](https://dashboard.ngrok.com/domains)
2. Use it:

```sh
ngrok http 3000 --url=your-subdomain.ngrok-free.app
```

Update the systemd service accordingly.

---

## Quick Reference

| Service | Port | Access |
|---|---|---|
| PostgreSQL | 5436 | localhost only |
| Web server + WebSocket | 3000 | localhost + ngrok |
| ngrok tunnel | — | `https://xxxx.ngrok-free.app` |
| ROS2 nodes | — | localhost (internal) |

| Command | Purpose |
|---|---|
| `npm run db:start` | Start PostgreSQL container |
| `npm start` | Start production web server |
| `ngrok http 3000` | Expose dashboard to internet |
| `sudo systemctl start ihm-web` | Start web server as service |
| `sudo systemctl status ihm-*` | Check all services |
| `journalctl -u ihm-web -f` | Tail web server logs |
