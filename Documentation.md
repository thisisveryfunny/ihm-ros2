# Guide de démarrage ROS 2 du robot IHM

Ce guide explique comment démarrer l'interface du robot ROS 2, l'agent Micro-ROS, le serveur de caméra, le nœud de détection IA, le serveur web et `ws_control_node`.

## Prérequis

- Docker installé
- Environnement ROS 2 disponible
- Accès au périphérique série du robot, généralement `/dev/ttyUSB0`
- Projet situé dans :

```bash
~/ihm-ros2
```

Utiliser le même `ROS_DOMAIN_ID` dans tous les terminaux :

```bash
export ROS_DOMAIN_ID=25
```

## 1. Entrer dans le conteneur Docker ROS 2

Ouvrir **Terminal 1**.

```bash
export ROS_DOMAIN_ID=25
sudo sh ~/script.sh
```

Cette étape peut prendre un certain temps.

## 2. Démarrer l'agent Micro-ROS

Ouvrir **Terminal 2**.

```bash
export ROS_DOMAIN_ID=25
```

Lancer le conteneur Docker de l'agent Micro-ROS :

```bash
docker run -it --rm \
  -e ROS_DOMAIN_ID=25 \
  -v /dev:/dev \
  -v /dev/shm:/dev/shm \
  --privileged \
  --net=host \
  microros/micro-ros-agent:humble serial \
  --dev /dev/ttyUSB0 \
  -b 921600 \
  -v4
```

Cela connecte ROS 2 au microcontrôleur via le port série.

## 3. Créer le package ROS 2

Dans **Terminal 1**, à l'intérieur du conteneur Docker ROS 2 :

```bash
export ROS_DOMAIN_ID=25
```

Créer l'espace de travail ROS 2 et le package :

```bash
mkdir -p ~/ros2_ws/src
cd ~/ros2_ws/src
```

```bash
ros2 pkg create \
  --build-type ament_python \
  --node-name ws_control_node \
  ihm_robot \
  --dependencies rclpy std_msgs sensor_msgs geometry_msgs nav_msgs
```

Aller dans le dossier du package Python :

```bash
cd ~/ros2_ws/src/ihm_robot/ihm_robot/
```

Copier le contenu du fichier situé à l'extérieur du conteneur Docker :

```bash
~/ihm-ros2/robot/ws_control_node.py
```

Le copier vers le fichier suivant, dans le conteneur :

```bash
~/ros2_ws/src/ihm_robot/ihm_robot/ws_control_node.py
```

## 4. Vérifier l'adresse IP réseau

Vérifier toujours l'adresse IP Ethernet ou Wi-Fi afin que l'interface web utilise la bonne adresse IP.

Pour vérifier l'adresse IP Wi-Fi :

```bash
ip -4 addr show wlan0 | awk '/inet / {print $2}' | cut -d/ -f1
```

Utiliser cette adresse IP pour configurer la connexion web.

Dans le fichier `robot/ws_control_node.py`, vérifier que les constantes suivantes pointent vers l'adresse IP du serveur web :

```python
WS_SERVER = "ws://10.10.211.145:5173/ws?role=robot"
WS_CAMERA_SERVER = "ws://10.10.211.145:5173/ws/camera?role=robot"
API_BASE = "http://10.10.211.145:5173/api"
```

Remplacer `10.10.211.145` par l'adresse IP réelle du poste qui exécute `npm run dev`.

## 5. Démarrer le conteneur Docker de la caméra

Ouvrir **Terminal 3**.

```bash
export ROS_DOMAIN_ID=25
cd ~/ihm-ros2
```

Démarrer le serveur de caméra MediaMTX :

```bash
sudo docker run --rm -it \
  --network=host \
  bluenviron/mediamtx:1
```

## 6. Démarrer le nœud de détection IA

Ouvrir **Terminal 4**.

Aller dans le dossier du projet si nécessaire :

```bash
cd ~/ihm-ros2
```

Créer un environnement virtuel Python :

```bash
python3 -m venv myenv
```

Activer l'environnement virtuel :

```bash
source myenv/bin/activate
```

Sourcer ROS 2 Jazzy :

```bash
source /opt/ros/jazzy/setup.bash
```

Installer les dépendances Python :

```bash
pip install -r requirements.txt
```

Lancer le nœud de détection IA avec `sudo` tout en conservant l'environnement ROS :

```bash
sudo env \
  PYTHONPATH="$PYTHONPATH" \
  LD_LIBRARY_PATH="$LD_LIBRARY_PATH" \
  AMENT_PREFIX_PATH="$AMENT_PREFIX_PATH" \
  CMAKE_PREFIX_PATH="$CMAKE_PREFIX_PATH" \
  ROS_DISTRO="$ROS_DISTRO" \
  ROS_VERSION="$ROS_VERSION" \
  ROS_PYTHON_VERSION="$ROS_PYTHON_VERSION" \
  /home/user/ihm-ros2/myenv/bin/python \
  /home/user/ihm-ros2/ros2_ai_detector.py
```

## 7. Démarrer le serveur web

Ouvrir un autre terminal.

```bash
export ROS_DOMAIN_ID=25
cd ~/ihm-ros2
```

Démarrer le serveur de développement web :

```bash
npm run dev
```

Le serveur Vite écoute généralement sur le port `5173`. Les API HTTP et les WebSockets sont exposés par ce même serveur.

## 8. Compiler et démarrer `ws_control_node`

Retourner dans **Terminal 1**, à l'intérieur du conteneur Docker ROS 2.

Aller dans l'espace de travail ROS 2 :

```bash
cd ~/ros2_ws
```

Installer les dépendances Python nécessaires :

```bash
pip install requests websockets opencv-python mediapipe
```

Compiler le package ROS 2 :

```bash
colcon build --packages-select ihm_robot
```

Sourcer l'espace de travail :

```bash
source install/setup.bash
```

Démarrer le nœud :

```bash
ros2 run ihm_robot ws_control_node
```

## API HTTP

Les API HTTP servent à enregistrer et à lire les données de télémétrie du robot dans PostgreSQL.

URL de base en développement :

```text
http://<IP_SERVEUR_WEB>:5173/api
```

Exemple avec l'adresse IP présente dans `ws_control_node.py` :

```text
http://10.10.211.145:5173/api
```

Le nœud `ws_control_node` publie les données vers ces points de terminaison avec un délai minimal de `1` seconde par type de donnée.

### `GET /api/batterie`

Renvoie toutes les mesures de batterie, triées de la plus récente à la plus ancienne.

Exemple :

```bash
curl http://10.10.211.145:5173/api/batterie
```

Réponse :

```json
[
  {
    "id": 1,
    "percentage": 85.5,
    "createdAt": "2026-05-11T12:00:00.000Z"
  }
]
```

### `POST /api/batterie`

Ajoute une mesure de batterie.

Requête :

```bash
curl -X POST http://10.10.211.145:5173/api/batterie \
  -H "Content-Type: application/json" \
  -d '{"percentage":85.5}'
```

Corps JSON :

```json
{
  "percentage": 85.5
}
```

Réponse : ligne créée, avec le code HTTP `201`.

### `GET /api/vitesse`

Renvoie toutes les mesures de vitesse, triées de la plus récente à la plus ancienne.

Exemple :

```bash
curl http://10.10.211.145:5173/api/vitesse
```

Réponse :

```json
[
  {
    "id": 1,
    "speed": 0.3,
    "createdAt": "2026-05-11T12:00:00.000Z"
  }
]
```

### `POST /api/vitesse`

Ajoute une mesure de vitesse linéaire.

Requête :

```bash
curl -X POST http://10.10.211.145:5173/api/vitesse \
  -H "Content-Type: application/json" \
  -d '{"speed":0.3}'
```

Corps JSON :

```json
{
  "speed": 0.3
}
```

Réponse : ligne créée, avec le code HTTP `201`.

### `GET /api/imu`

Renvoie toutes les mesures IMU, triées de la plus récente à la plus ancienne.

Exemple :

```bash
curl http://10.10.211.145:5173/api/imu
```

Réponse :

```json
[
  {
    "id": 1,
    "accelX": 0.01,
    "accelY": 0.02,
    "accelZ": 9.81,
    "gyroX": 0.001,
    "gyroY": 0.002,
    "gyroZ": 0.003,
    "createdAt": "2026-05-11T12:00:00.000Z"
  }
]
```

### `POST /api/imu`

Ajoute une mesure IMU.

Requête :

```bash
curl -X POST http://10.10.211.145:5173/api/imu \
  -H "Content-Type: application/json" \
  -d '{"accel_x":0.01,"accel_y":0.02,"accel_z":9.81,"gyro_x":0.001,"gyro_y":0.002,"gyro_z":0.003}'
```

Corps JSON :

```json
{
  "accel_x": 0.01,
  "accel_y": 0.02,
  "accel_z": 9.81,
  "gyro_x": 0.001,
  "gyro_y": 0.002,
  "gyro_z": 0.003
}
```

Réponse : ligne créée, avec le code HTTP `201`.

### Résumé des points de terminaison de l'API

| Méthode | Point de terminaison | Rôle | Corps attendu |
|---|---|---|---|
| `GET` | `/api/batterie` | Lire l'historique de la batterie | Aucun |
| `POST` | `/api/batterie` | Enregistrer une mesure de batterie | `{ "percentage": number }` |
| `GET` | `/api/vitesse` | Lire l'historique de la vitesse | Aucun |
| `POST` | `/api/vitesse` | Enregistrer une mesure de vitesse | `{ "speed": number }` |
| `GET` | `/api/imu` | Lire l'historique IMU | Aucun |
| `POST` | `/api/imu` | Enregistrer une mesure IMU | `{ "accel_x": number, "accel_y": number, "accel_z": number, "gyro_x": number, "gyro_y": number, "gyro_z": number }` |

## WebSockets

Le serveur web expose deux WebSockets :

| Point de terminaison | Rôle |
|---|---|
| `/ws` | Contrôle du déplacement, alertes du robot et signalisation WebRTC |
| `/ws/camera` | Contrôle des servomoteurs de caméra |

Les connexions utilisent un paramètre `role` :

| Rôle | Exemple | Description |
|---|---|---|
| `robot` | `ws://10.10.211.145:5173/ws?role=robot` | Connexion utilisée par `ws_control_node` |
| `controller` | `ws://10.10.211.145:5173/ws?role=controller` | Connexion utilisée par l'interface web |

Si `role` n'est pas `robot`, le serveur traite la connexion comme un contrôleur.

Le serveur envoie un signal de vie WebSocket interne toutes les `30` secondes. Les clients applicatifs peuvent aussi envoyer `{ "type": "ping" }` et recevront `{ "type": "pong" }`.

### WebSocket `/ws`

Ce WebSocket sert au contrôle de déplacement et aux alertes du robot.

URL du robot :

```text
ws://10.10.211.145:5173/ws?role=robot
```

URL de l'interface web :

```text
ws://10.10.211.145:5173/ws?role=controller
```

#### Commande de déplacement

Envoyée par le contrôleur, puis relayée vers les connexions du robot.

```json
{
  "type": "command",
  "direction": "front",
  "speedMode": "normal"
}
```

Directions valides :

```text
front, back, left, right, stop
```

Modes de vitesse valides :

```text
lent, normal, rapide
```

Dans `ws_control_node`, les modes correspondent aux vitesses linéaires suivantes :

| Mode | Vitesse linéaire |
|---|---:|
| `lent` | `0.3` |
| `normal` | `0.5` |
| `rapide` | `0.7` |

Comportement ROS 2 côté robot :

| Direction | Publication ROS 2 |
|---|---|
| `front` | `/cmd_vel`, `linear.x > 0`, sauf si obstacle détecté |
| `back` | `/cmd_vel`, `linear.x < 0` |
| `left` | `/cmd_vel`, `angular.z = 1.0` |
| `right` | `/cmd_vel`, `angular.z = -1.0` |
| `stop` | `/cmd_vel`, vitesse nulle |

#### Statut de connexion

Envoyé aux contrôleurs pour indiquer le nombre de robots connectés.

```json
{
  "type": "status",
  "connectedRobots": 1
}
```

#### Ping applicatif

Requête :

```json
{
  "type": "ping"
}
```

Réponse :

```json
{
  "type": "pong"
}
```

#### Alerte collision

Envoyée par le robot, puis relayée vers les contrôleurs.

```json
{
  "type": "collision-alert",
  "distance": 0.25,
  "blocked": true
}
```

Le champ `blocked` vaut `true` quand un obstacle est détecté devant le robot, et `false` quand le passage redevient libre.

#### Détection de panneau

Le protocole accepte aussi un message de détection de panneau.

```json
{
  "type": "sign-detected",
  "sign": "stop"
}
```

Valeurs valides pour `sign` :

```text
stop, up, down, left, right, null
```

#### Signalisation WebRTC

Le WebSocket `/ws` relaie aussi les messages de signalisation WebRTC entre robot et contrôleur.

Offre :

```json
{
  "type": "webrtc-offer",
  "sdp": "..."
}
```

Réponse :

```json
{
  "type": "webrtc-answer",
  "sdp": "..."
}
```

Candidat ICE :

```json
{
  "type": "webrtc-ice",
  "candidate": "...",
  "sdpMid": "0",
  "sdpMLineIndex": 0
}
```

### WebSocket `/ws/camera`

Ce WebSocket est dédié au contrôle pan/tilt de la caméra. Il est séparé du contrôle de déplacement.

URL du robot :

```text
ws://10.10.211.145:5173/ws/camera?role=robot
```

URL de l'interface web :

```text
ws://10.10.211.145:5173/ws/camera?role=controller
```

#### Commande de caméra

Envoyée par le contrôleur, puis relayée vers les connexions du robot.

```json
{
  "type": "camera",
  "direction": "left"
}
```

Directions valides :

```text
up, down, left, right, stop
```

Comportement ROS 2 côté robot :

| Direction | Action |
|---|---|
| `left` | Déplace le servo pan vers la gauche |
| `right` | Déplace le servo pan vers la droite |
| `up` | Déplace le servo tilt vers le haut |
| `down` | Déplace le servo tilt vers le bas |
| `stop` | Arrête le mouvement des servos |

Les commandes de caméra publient sur les topics ROS 2 suivants :

| Topic | Rôle |
|---|---|
| `/servo_s1` | Pan horizontal |
| `/servo_s2` | Tilt vertical |

#### Statut et ping de la caméra

Le WebSocket de caméra utilise les mêmes messages de statut et de ping que `/ws`.

Statut :

```json
{
  "type": "status",
  "connectedRobots": 1
}
```

Ping :

```json
{
  "type": "ping"
}
```

Pong :

```json
{
  "type": "pong"
}
```

#### Erreur de message

Si un message JSON est invalide ou ne respecte pas le protocole, le serveur répond :

```json
{
  "type": "error",
  "message": "Invalid message"
}
```

## Liens ROS 2 utilisés par `ws_control_node`

| Type | Topic ROS 2 | Rôle |
|---|---|---|
| Publisher | `/cmd_vel` | Commandes de déplacement du robot |
| Publisher | `/servo_s1` | Servo pan de la caméra |
| Publisher | `/servo_s2` | Servo tilt de la caméra |
| Subscriber | `/scan` | Détection d'un obstacle frontal |
| Subscriber | `/battery` | Mesure de la batterie |
| Subscriber | `/imu` | Accélération et gyroscope |
| Subscriber | `/odom_raw` | Vitesse linéaire |

## Résumé des terminaux

| Terminal | Rôle | Commande / Processus |
|---|---|---|
| Terminal 1 | Conteneur Docker ROS 2 et `ws_control_node` | `sudo sh ~/script.sh`, puis compilation et lancement du package ROS |
| Terminal 2 | Agent Micro-ROS | Conteneur Docker `microros/micro-ros-agent:humble` |
| Terminal 3 | Serveur de caméra | Conteneur Docker `bluenviron/mediamtx:1` |
| Terminal 4 | Nœud de détection IA | `ros2_ai_detector.py` |
| Terminal 5 | Serveur web | `npm run dev` |

## Ordre de démarrage recommandé

1. Entrer dans le conteneur Docker ROS 2.
2. Démarrer l'agent Micro-ROS.
3. Démarrer le serveur de caméra.
4. Démarrer le nœud de détection IA.
5. Démarrer le serveur web.
6. Compiler et lancer `ws_control_node`.

## Vérifications utiles

Vérifier que le périphérique série existe :

```bash
ls /dev/ttyUSB0
```

Vérifier le `ROS_DOMAIN_ID` :

```bash
echo $ROS_DOMAIN_ID
```

Vérifier l'adresse IP réseau du robot :

```bash
ip -4 addr show wlan0 | awk '/inet / {print $2}' | cut -d/ -f1
```

Vérifier les topics ROS 2 disponibles :

```bash
ros2 topic list
```

Vérifier les nœuds ROS 2 actifs :

```bash
ros2 node list
```

Tester l'API batterie :

```bash
curl http://10.10.211.145:5173/api/batterie
```

Tester l'API vitesse :

```bash
curl http://10.10.211.145:5173/api/vitesse
```

Tester l'API IMU :

```bash
curl http://10.10.211.145:5173/api/imu
```
