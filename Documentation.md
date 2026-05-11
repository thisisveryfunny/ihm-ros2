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

### Depot du projet

Les commandes ci-dessous supposent que le projet est place dans :

```bash
cd ~/ihm-ros2
```

Si le dossier porte un autre nom, remplacer `~/ihm-ros2` par le chemin reel du projet.

---

## 3. Configuration initiale de l'application web

Installer les dependances Node.js :

```bash
npm install
```

Creer le fichier `.env` a la racine du projet :

```bash
cat > .env << 'EOF'
DATABASE_URL=postgresql://ros2:ros2@localhost:5436/ros2
PORT=3000
HOST=0.0.0.0
EOF
```

Demarrer PostgreSQL :

```bash
npm run db:start
```

Verifier que la base est disponible :

```bash
docker exec ros2-yaboom-ihm pg_isready -U ros2 -d ros2
```

Initialiser ou synchroniser le schema de base de donnees :

```bash
npm run db:push
```

---

## 4. Execution en developpement avec `npm run dev`

Le mode developpement sert pendant les tests, les demonstrations locales et les ajustements de l'interface.

Commande :

```bash
npm run dev
```

Ce script lance :

```bash
vite dev --host
```

Concretement, cela demarre le serveur Vite/SvelteKit en mode developpement.

### Caracteristiques du mode developpement

| Element | Description |
|---|---|
| Port par defaut | `5173` |
| URL locale | `http://localhost:5173` |
| Acces reseau | Active par `--host`, donc accessible depuis une autre machine du meme reseau |
| Rechargement automatique | Oui, les modifications du code sont rechargees automatiquement |
| WebSocket robot | Disponible sur `/ws` |
| API REST | Disponible sur `/api/batterie`, `/api/vitesse`, `/api/imu` |
| Usage recommande | Developpement et tests locaux uniquement |

Apres le lancement, Vite affiche une sortie semblable a :

```text
Local:   http://localhost:5173/
Network: http://192.168.x.x:5173/
```

Pour utiliser l'interface depuis un autre appareil du meme reseau, ouvrir l'URL `Network` dans le navigateur.

### Point important pour le robot

En mode developpement, les noeuds robot doivent pointer vers le port `5173`.

Exemples :

```bash
python3 telemetry_node.py --ros-args -p server_url:=http://192.168.x.x:5173
python3 control_node.py --ros-args -p server_url:=192.168.x.x:5173
python3 collision_node.py --ros-args -p server_url:=192.168.x.x:5173
SERVER_URL=192.168.x.x:5173 python3 camera_node.py
python3 sign_detection_node.py --ros-args -p server_url:=192.168.x.x:5173
```

Remplacer `192.168.x.x` par l'adresse IP de la machine qui execute `npm run dev`.

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

### 5.4 Verification rapide apres demarrage

Tester l'API batterie :

```bash
curl http://localhost:3000/api/batterie
```

Si la base est accessible, la reponse doit etre un tableau JSON, par exemple :

```json
[]
```

---

## 6. Procedure complete de demarrage du robot

Les etapes suivantes decrivent le lancement manuel complet du systeme.

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

#### Option recommandee pour la remise client : production

```bash
export ROS_DOMAIN_ID=25
cd ~/ihm-ros2

npm run db:start
npm run build
npm start
```

Le tableau de bord est alors disponible sur le port `3000`.

#### Option developpement : `npm run dev`

```bash
export ROS_DOMAIN_ID=25
cd ~/ihm-ros2

npm run db:start
npm run dev
```

Le tableau de bord est alors disponible sur le port `5173`.

### Terminal 4 - Creation du package ROS2 si necessaire

Cette etape est requise seulement si le package `ihm_robot` n'existe pas deja dans le workspace ROS2.

Dans le conteneur ROS2 :

```bash
export ROS_DOMAIN_ID=25

mkdir -p ~/ros2_ws/src
cd ~/ros2_ws/src

ros2 pkg create \
  --build-type ament_python \
  --node-name ws_control_node \
  ihm_robot \
  --dependencies rclpy std_msgs sensor_msgs geometry_msgs nav_msgs
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

Dans le conteneur ROS2 :

```bash
export ROS_DOMAIN_ID=25

cd ~/ros2_ws
pip install requests websockets opencv-python mediapipe

colcon build --packages-select ihm_robot
source install/setup.bash

ros2 run ihm_robot ws_control_node
```

---

## 7. Commandes robot Python disponibles

Le dossier `robot/` contient aussi les noeuds Python executables directement.

Installation :

```bash
cd ~/ihm-ros2/robot
pip install -r requirements.txt
source /opt/ros/humble/setup.bash
```

### En developpement

Utiliser le port `5173` :

```bash
python3 telemetry_node.py --ros-args -p server_url:=http://ADRESSE_IP_SERVEUR:5173
python3 control_node.py --ros-args -p server_url:=ADRESSE_IP_SERVEUR:5173
python3 collision_node.py --ros-args -p server_url:=ADRESSE_IP_SERVEUR:5173
SERVER_URL=ADRESSE_IP_SERVEUR:5173 python3 camera_node.py
python3 sign_detection_node.py --ros-args -p server_url:=ADRESSE_IP_SERVEUR:5173
```

### En production

Utiliser le port `3000` :

```bash
python3 telemetry_node.py --ros-args -p server_url:=http://ADRESSE_IP_SERVEUR:3000
python3 control_node.py --ros-args -p server_url:=ADRESSE_IP_SERVEUR:3000
python3 collision_node.py --ros-args -p server_url:=ADRESSE_IP_SERVEUR:3000
SERVER_URL=ADRESSE_IP_SERVEUR:3000 python3 camera_node.py
python3 sign_detection_node.py --ros-args -p server_url:=ADRESSE_IP_SERVEUR:3000
```

---

## 8. Camera RTSP historique

Une ancienne procedure de camera RTSP peut etre utilisee si necessaire.

Demarrer MediaMTX :

```bash
export ROS_DOMAIN_ID=25
cd ~/ihm-ros2

sudo docker run --rm -it --network=host bluenviron/mediamtx:1
```

Demarrer ensuite `ffmpeg` avec la camera :

```bash
sudo ffmpeg \
  -f v4l2 \
  -s 640x480 \
  -framerate 30 \
  -i /dev/video0 \
  -c:v libx264 \
  -preset veryfast \
  -tune zerolatency \
  -f rtsp \
  rtsp://localhost:8554/robot
```

Cette procedure est separee du flux WebRTC implemente par `camera_node.py`.

---

## 9. Ordre de demarrage recommande

Pour une demonstration ou une remise client :

1. Demarrer PostgreSQL : `npm run db:start`
2. Construire l'application : `npm run build`
3. Demarrer le serveur : `npm start`
4. Demarrer l'agent MicroROS
5. Demarrer les noeuds ROS2/Python
6. Ouvrir le tableau de bord dans le navigateur
7. Verifier que le robot est connecte et que les donnees arrivent

---

## 10. Depannage rapide

| Probleme | Verification |
|---|---|
| Le tableau de bord ne s'ouvre pas | Verifier que `npm run dev` ou `npm start` est actif |
| Les donnees restent vides | Verifier PostgreSQL, `.env`, puis `npm run db:push` |
| Le robot ne recoit pas les commandes | Verifier l'URL WebSocket, le port et l'adresse IP serveur |
| Le navigateur ne rejoint pas le serveur | Verifier que `HOST=0.0.0.0` en production ou que `npm run dev` utilise bien `--host` |
| Le port serie MicroROS echoue | Verifier le peripherique `/dev/ttyUSB0` |
| La camera ne fonctionne pas | Verifier `/dev/video0` et qu'un seul processus utilise la camera |

---

## 11. Resume des commandes principales

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
