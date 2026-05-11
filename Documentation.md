# Documentation de remise - Projet IHM ROS2

## 1. Objectif du projet

Ce projet fournit une interface web de supervision et de controle pour un robot Yahboom MicroROS-Pi5.

L'application permet de :

- visualiser les donnees de telemetrie du robot : batterie, vitesse et IMU;
- controler les mouvements du robot depuis le navigateur;
- afficher les alertes de collision;
- recevoir les evenements de detection de panneaux;
- exposer une interface web accessible en reseau local ou via une mise en production.

Le systeme est compose de quatre parties principales :

| Composant | Role |
|---|---|
| Application web SvelteKit | Tableau de bord utilise par le client |
| Serveur Node.js | Sert l'application, les API REST et le WebSocket `/ws` |
| Base PostgreSQL | Stocke les donnees de telemetrie |
| Noeuds ROS2/Python | Lisent les capteurs et pilotent le robot |

---

## 2. Prerequis

### Machine serveur / robot

- Node.js 20 recommande
- npm
- Docker et Docker Compose
- ROS2 Humble
- Python 3.10+
- Acces aux peripheriques du robot : camera, lidar, port serie MicroROS

---

## 3. Répertoire GitHub 

### Code source disponible sur GitHub
https://github.com/thisisveryfunny/ihm-ros2

Pour clôner le répertoire:
```bash
git clone https://github.com/thisisveryfunny/ihm-ros2.git
```
---

## 4. Execution en developpement avec `npm run dev`

Le mode developpement sert pendant les tests, les demonstrations locales et les ajustements de l'interface.

Commande :

```bash
cd ~/ihm-ros2
npm run dev
```

Concretement, cela demarre le serveur Vite/SvelteKit en mode developpement.

### Caracteristiques du mode developpement

| Element | Description |
|---|---|
| Port par defaut | `5173` |
| URL locale | `http://localhost:5173` |
| Acces reseau | Active par `--host`, donc accessible depuis une autre machine du meme reseau |
| WebSocket robot | Disponible sur `/ws` |
| API REST | Disponible sur `/api/batterie`, `/api/vitesse`, `/api/imu` |
| Usage recommande | Developpement et tests locaux uniquement |

Apres le lancement, Vite affiche une sortie semblable a :

```text
Local:   http://localhost:5173/
Network: http://192.168.x.x:5173/ ou http://10.10.211.x:5173/
```

Pour utiliser l'interface depuis un autre appareil du meme reseau, ouvrir l'URL `Network` dans le navigateur.

### Point important pour le robot

En mode developpement, le fichier `robot/ws_control_node.py` doit pointer vers l'adresse IP de la machine qui execute `npm run dev`, avec le port `5173`.

Les valeurs a verifier dans `robot/ws_control_node.py` sont :

```python
WS_SERVER = "ws://ADRESSE_IP_SERVEUR:5173/ws?role=robot"
WS_CAMERA_SERVER = "ws://ADRESSE_IP_SERVEUR:5173/ws/camera?role=robot"
API_BASE = "http://ADRESSE_IP_SERVEUR:5173/api"
```

Remplacer `ADRESSE_IP_SERVEUR` par l'adresse IP reelle de la machine qui execute l'application web.

Pour trouver l'adresse IP Wi-Fi du robot ou du serveur :

```bash
ip -4 addr show wlan0 | awk '/inet / {print $2}' | cut -d/ -f1
```

Si la connexion utilise Ethernet, remplacer `wlan0` par l'interface reseau correspondante, par exemple `eth0`.

---

## 5. Build production

Le mode production doit etre utilise pour la remise client ou l'exploitation normale.

Contrairement a `npm run dev`, il ne lance pas Vite en mode developpement. Il compile l'application dans le dossier `build/`, puis `server.js` sert cette version compilee avec le WebSocket de production.

### 5.1 Construire l'application

```bash
npm run build
```

Cette commande execute :

```bash
vite build
```

Resultat attendu :

- generation du dossier `build/`;
- compilation de l'application SvelteKit;
- preparation des fichiers necessaires au serveur Node.js de production.

### 5.2 Demarrer le serveur production

```bash
npm start
```

Cette commande execute :

```bash
node server.js
```

Le serveur ecoute par defaut sur :

```text
http://0.0.0.0:3000
```

Depuis la machine locale :

```text
http://localhost:3000
```

Depuis un autre appareil du meme reseau :

```text
http://ADRESSE_IP_DU_SERVEUR:3000
```

### 5.3 Variables d'environnement production

Le fichier `.env` recommande pour la production est :

```bash
DATABASE_URL=postgresql://ros2:ros2@localhost:5436/ros2
PORT=3000
HOST=0.0.0.0
```

| Variable | Description |
|---|---|
| `DATABASE_URL` | Connexion PostgreSQL utilisee par l'application |
| `PORT` | Port HTTP du serveur de production |
| `HOST` | Adresse d'ecoute. `0.0.0.0` permet l'acces depuis le reseau |

---

## 6. Procedure complete de demarrage du robot

Les etapes suivantes reprennent la procedure de lancement utilisee pour le robot.

Source de reference des commandes robot :

```text
/Users/return/Obsidian/main/Yahboom_robot_commands.md
```

### Terminal 1 - Environnement ROS2 du robot

Entrer dans l'environnement ROS2 Docker fourni sur le robot :

```bash
export ROS_DOMAIN_ID=25
sudo sh ~/script.sh
```

Cette etape peut prendre du temps.

### Terminal 2 - Agent MicroROS

Lancer l'agent MicroROS pour communiquer avec le controleur du robot :

```bash
export ROS_DOMAIN_ID=25

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

Si le robot utilise un autre port serie, adapter `/dev/ttyUSB0`.

### Terminal 3 - Application web

La procedure historique lance le serveur web en mode developpement :

```bash
export ROS_DOMAIN_ID=25
cd ~/ihm-ros2

npm run dev
```

Le tableau de bord est alors disponible sur le port `5173`.

Pour une remise client en mode production, remplacer `npm run dev` par :

```bash
export ROS_DOMAIN_ID=25
cd ~/ihm-ros2

npm run build
npm start
```

Le tableau de bord est alors disponible sur le port `3000`.

### Terminal 4 - Creation du package ROS2

Dans le conteneur ROS2 ouvert au Terminal 1 :

```bash
export ROS_DOMAIN_ID=25

mkdir -p ~/ros2_ws/src && cd ~/ros2_ws/src

ros2 pkg create --build-type ament_python --node-name ws_control_node ihm_robot --dependencies rclpy std_msgs sensor_msgs geometry_msgs nav_msgs

cd ~/ros2_ws/src/ihm_robot/ihm_robot/
```

Copier ensuite le contenu du fichier :

```text
~/ihm-ros2/robot/ws_control_node.py
```

vers :

```text
~/ros2_ws/src/ihm_robot/ihm_robot/ws_control_node.py
```

### Terminal 5 - Compilation et lancement du noeud de controle

```bash
cd ~/ros2_ws
pip install requests websockets opencv-python mediapipe
colcon build --packages-select ihm_robot
source install/setup.bash
ros2 run ihm_robot ws_control_node
```

---

## 7. Camera RTSP

La procedure de lancement utilise un conteneur MediaMTX et une commande `ffmpeg` pour publier le flux camera RTSP.

### Terminal 6 - MediaMTX

```bash
export ROS_DOMAIN_ID=25
cd ~/ihm-ros2

sudo docker run --rm -it --network=host bluenviron/mediamtx:1
```

### Terminal 7 - ffmpeg

Dans la procedure de reference, la commande exacte est recuperee avec :

```bash
export ROS_DOMAIN_ID=25
cd ~/ihm-ros2
cat setup
```

La commande attendue est de cette forme et doit etre lancee avec `sudo` :

```bash
sudo ffmpeg -f v4l2 -s 640x480 -framerate 30 -i /dev/video0 -c:v libx264 -preset veryfast -tune zerolatency -f rtsp rtsp://localhost:8554/robot
```

---

## 8. Ordre de demarrage recommande

Pour une demonstration ou une remise client :

1. Entrer dans le Docker ROS2 avec `sudo sh ~/script.sh`
2. Demarrer l'agent MicroROS
3. Creer ou verifier le package ROS2 `ihm_robot`
4. Demarrer MediaMTX
5. Demarrer `ffmpeg`
6. Demarrer le serveur web
7. Compiler et lancer `ws_control_node.py`
8. Ouvrir le tableau de bord dans le navigateur
9. Verifier que le robot est connecte et que les commandes repondent

---

## 9. Depannage rapide

| Probleme | Verification |
|---|---|
| Le tableau de bord ne s'ouvre pas | Verifier que `npm run dev` ou `npm start` est actif |
| Les donnees restent vides | Verifier PostgreSQL, `.env`, puis `npm run db:push` |
| Le robot ne recoit pas les commandes | Verifier l'URL WebSocket, le port et l'adresse IP serveur |
| Le navigateur ne rejoint pas le serveur | Verifier que `HOST=0.0.0.0` en production ou que `npm run dev` utilise bien `--host` |
| Le port serie MicroROS echoue | Verifier le peripherique `/dev/ttyUSB0` |
| La camera ne fonctionne pas | Verifier `/dev/video0` et qu'un seul processus utilise la camera |

---

## 10. Resume des commandes principales

### Developpement

```bash
npm install
npm run db:start
npm run db:push
npm run dev
```

Interface :

```text
http://localhost:5173
```

### Production

```bash
npm install
npm run db:start
npm run db:push
npm run build
npm start
```

Interface :

```text
http://localhost:3000
```

### Verification production

```bash
curl http://localhost:3000/api/batterie
```
