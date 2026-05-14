# IHM ROS2

Tableau de bord web pour un robot Yahboom MicroROS-Pi5. L’application affiche la télémétrie du robot, permet le contrôle à distance des déplacements, contrôle les servos pan/tilt de la caméra, affiche un flux vidéo et remonte les alertes de collision.

## Architecture actuelle

```
+--------------------------------+          +--------------------------------+
|          ROBOT (Pi5)           |          |      WEB SERVER (SvelteKit)    |
|                                |          |                                |
|  ws_control_node.py            |          |  REST API                      |
|    /battery  ----HTTP POST----------->    |    /api/batterie               |
|    /odom_raw ----HTTP POST----------->    |    /api/vitesse                |
|    /imu      ----HTTP POST----------->    |    /api/imu                    |
|                                |          |        |                       |
|    /scan                       |          |        v                       |
|    -> collision-alert --WS----------->    |  PostgreSQL                    |
|                                |          |                                |
|    <------------- WS command ---------    |  /ws                           |
|    -> /cmd_vel                 |          |  déplacement + alertes         |
|                                |          |                                |
|    <------------- WS camera ----------    |  /ws/camera                    |
|    -> /servo_s1, /servo_s2     |          |  contrôle pan/tilt caméra      |
|                                |          +--------------------------------+
|  ros2_ai_detector.py           |                         ^
|    /dev/video0 -> MediaPipe    |                         |
|    -> RTSP MediaMTX            |                         v
+--------------------------------+                  +--------------+
                                                    |  DASHBOARD   |
                                                    |  navigateur  |
                                                    +--------------+
```

Le dépôt ne contient plus des nodes séparés comme `telemetry_node.py`, `control_node.py`, `collision_node.py` ou `camera_node.py`. Les responsabilités robot principales sont maintenant regroupées dans `robot/ws_control_node.py`, avec un script séparé `robot/ros2_ai_detector.py` pour le flux caméra annoté.

## Structure du projet

```
ihm-ros2/
├── src/                          # Application SvelteKit
│   ├── routes/                    # Pages dashboard et endpoints API
│   │   ├── api/batterie/
│   │   ├── api/vitesse/
│   │   ├── api/imu/
│   │   ├── battery/
│   │   ├── speed/
│   │   ├── imu/
│   │   └── remote-control/
│   ├── lib/server/db/             # Schéma Drizzle et connexion PostgreSQL
│   ├── lib/server/ws/             # Protocoles WebSocket et relais
│   ├── lib/services/              # Clients API et WebSocket côté navigateur
│   └── lib/components/            # Composants UI, graphiques et contrôle robot
├── robot/
│   ├── ws_control_node.py         # Télémétrie, déplacement, collision, servos caméra
│   ├── ros2_ai_detector.py        # Détection MediaPipe et stream RTSP via ffmpeg
│   └── requirements.txt           # Dépendances Python robot
├── db/
│   ├── docker-compose.yml         # PostgreSQL local
│   └── init.sql                   # Tables batterie, vitesse, imu
├── docs/                          # Documentation complémentaire
├── server.js                      # Serveur production HTTP + WebSocket
└── vite.config.ts                 # Serveur dev avec WebSocket
```

## Flux principaux

### Télémétrie

`ws_control_node.py` lit les topics ROS 2, puis envoie les mesures vers les endpoints REST avec un délai minimal de `1` seconde par type de donnée.

```
/battery  -> ws_control_node.py -> POST /api/batterie -> batterie
/odom_raw -> ws_control_node.py -> POST /api/vitesse  -> vitesse
/imu      -> ws_control_node.py -> POST /api/imu      -> imu
```

Les pages `battery`, `speed` et `imu` lisent ensuite ces données avec les endpoints `GET` et les affichent dans le dashboard.

### Déplacement

```
Dashboard -> /ws -> ws_control_node.py -> /cmd_vel
```

Le contrôleur envoie des messages `command` avec une `direction` et un `speedMode`. Le robot publie ensuite un message `geometry_msgs/Twist` sur `/cmd_vel`.

Directions valides:

```text
front, back, left, right, stop
```

Modes de vitesse valides:

```text
lent, normal, rapide
```

Correspondance actuelle dans `ws_control_node.py`:

| Mode | Vitesse linéaire |
|---|---:|
| `lent` | `0.3` |
| `normal` | `0.5` |
| `rapide` | `0.7` |

### Collision

`ws_control_node.py` écoute `/scan` et vérifie la zone frontale. Si un obstacle est détecté à moins de `0.30 m`, le robot publie un arrêt sur `/cmd_vel` et envoie une alerte WebSocket aux contrôleurs.

```json
{ "type": "collision-alert", "distance": 0.25, "blocked": true }
```

Quand la voie est libre, le même message est envoyé avec `blocked: false`.

### Caméra et servos

Le contrôle pan/tilt passe par un WebSocket dédié:

```
Dashboard -> /ws/camera -> ws_control_node.py -> /servo_s1, /servo_s2
```

Directions valides:

```text
up, down, left, right, stop
```

Le flux vidéo affiché dans `CameraFeed.svelte` ne passe pas par le WebSocket `/ws`. Il utilise WHEP vers MediaMTX:

```text
http://<VITE_CAMERA_HOST ou location.hostname>:8889/robot/whep
```

`ros2_ai_detector.py` lit la caméra, annote les frames avec MediaPipe (visage, mains, points de pieds) et les pousse vers un flux RTSP, par défaut:

```text
rtsp://127.0.0.1:8554/robot
```

## REST API

| Méthode | Endpoint | Corps de requête | Réponse |
|---|---|---|---|
| POST | `/api/batterie` | `{ "percentage": 85.5 }` | `201` + ligne créée |
| GET | `/api/batterie` | Aucun | Toutes les lectures, plus récentes en premier |
| POST | `/api/vitesse` | `{ "speed": 1.23 }` | `201` + ligne créée |
| GET | `/api/vitesse` | Aucun | Toutes les lectures, plus récentes en premier |
| POST | `/api/imu` | `{ "accel_x": 0, "accel_y": 0, "accel_z": 0, "gyro_x": 0, "gyro_y": 0, "gyro_z": 0 }` | `201` + ligne créée |
| GET | `/api/imu` | Aucun | Toutes les lectures, plus récentes en premier |

Tous les enregistrements incluent un `id` et un `createdAt`.

## Schéma de base de données

```sql
batterie (
  id SERIAL PRIMARY KEY,
  percentage REAL NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
)

vitesse (
  id SERIAL PRIMARY KEY,
  speed REAL NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
)

imu (
  id SERIAL PRIMARY KEY,
  accel_x REAL NOT NULL,
  accel_y REAL NOT NULL,
  accel_z REAL NOT NULL,
  gyro_x REAL NOT NULL,
  gyro_y REAL NOT NULL,
  gyro_z REAL NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
)
```

## WebSockets

Le serveur expose deux WebSockets.

| Endpoint | Rôle |
|---|---|
| `/ws` | Déplacement, statut robot, alertes collision, messages `sign-detected`, relais WebRTC générique |
| `/ws/camera` | Contrôle des servos caméra |

Les connexions utilisent le paramètre `role`:

| Rôle | Exemple |
|---|---|
| Robot | `ws://host/ws?role=robot` |
| Controller | `ws://host/ws?role=controller` |
| Robot caméra | `ws://host/ws/camera?role=robot` |
| Controller caméra | `ws://host/ws/camera?role=controller` |

Si `role` n’est pas `robot`, le serveur traite la connexion comme un contrôleur.

### Messages `/ws`

```json
{ "type": "command", "direction": "front", "speedMode": "normal" }
{ "type": "status", "connectedRobots": 1 }
{ "type": "collision-alert", "distance": 0.25, "blocked": true }
{ "type": "sign-detected", "sign": "stop" }
{ "type": "sign-detected", "sign": null }
{ "type": "webrtc-offer", "sdp": "<SDP>" }
{ "type": "webrtc-answer", "sdp": "<SDP>" }
{ "type": "webrtc-ice", "candidate": "<candidate>", "sdpMid": "0", "sdpMLineIndex": 0 }
{ "type": "ping" }
{ "type": "pong" }
{ "type": "error", "message": "Invalid message" }
```

### Messages `/ws/camera`

```json
{ "type": "camera", "direction": "left" }
{ "type": "status", "connectedRobots": 1 }
{ "type": "ping" }
{ "type": "pong" }
{ "type": "error", "message": "Invalid message" }
```

## Topics ROS 2 utilisés

| Type | Topic | Message | Utilisation |
|---|---|---|---|
| Publisher | `/cmd_vel` | `geometry_msgs/Twist` | Commandes de déplacement |
| Publisher | `/servo_s1` | `std_msgs/Int32` | Servo pan caméra |
| Publisher | `/servo_s2` | `std_msgs/Int32` | Servo tilt caméra |
| Subscriber | `/scan` | `sensor_msgs/LaserScan` | Détection d’obstacle frontal |
| Subscriber | `/battery` | `std_msgs/UInt16` | Batterie, convertie en pourcentage |
| Subscriber | `/imu` | `sensor_msgs/Imu` | Accélération et gyroscope |
| Subscriber | `/odom_raw` | `nav_msgs/Odometry` | Vitesse linéaire |

## Installation du serveur web

### Prérequis

- Node.js 18+
- Docker et Docker Compose
- PostgreSQL lancé avec le fichier `db/docker-compose.yml`

### Démarrage local

```sh
npm install

# Démarrer PostgreSQL
npm run db:start

# Créer .env
echo "DATABASE_URL=postgresql://ros2:ros2@localhost:5436/ros2" > .env

# Appliquer le schéma
npm run db:push

# Démarrer le serveur de développement
npm run dev
```

Le serveur Vite écoute généralement sur `http://localhost:5173`. Les endpoints API et les WebSockets sont exposés sur le même serveur.

### Production

```sh
npm run build
npm start
```

`npm start` lance `server.js`, qui sert l’application et attache les WebSockets.

## Démarrage côté robot

Les étapes complètes de démarrage ROS 2, Micro-ROS, MediaMTX, `ros2_ai_detector.py` et `ws_control_node.py` sont documentées dans [Documentation.md](Documentation.md).

Points importants:

- Configurer `WS_SERVER`, `WS_CAMERA_SERVER` et `API_BASE` dans `robot/ws_control_node.py` avec l’adresse IP du serveur web.
- Utiliser le même `ROS_DOMAIN_ID` dans les terminaux ROS 2.
- Démarrer MediaMTX pour exposer le flux WHEP utilisé par le dashboard.
- Lancer `ws_control_node.py` dans un package ROS 2 ou avec l’environnement ROS 2 correctement sourcé.

## Variables utiles

| Variable | Utilisation |
|---|---|
| `DATABASE_URL` | Connexion PostgreSQL utilisée par Drizzle et les routes API |
| `VITE_WS_URL` | Base WebSocket optionnelle côté navigateur, sinon `location.host` est utilisé |
| `VITE_CAMERA_HOST` | Hôte optionnel pour le flux WHEP MediaMTX, sinon `location.hostname` est utilisé |

## Documentation complémentaire

- [Documentation.md](Documentation.md): guide de démarrage complet robot + serveur
- [docs/deployment.md](docs/deployment.md): notes de déploiement
- [docs/architecture.md](docs/architecture.md): documentation d’architecture plus détaillée, à valider si l’architecture change encore
