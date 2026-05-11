# 1. Go in ROS2 Docker (Terminal 1)
```bash
# Go in the ros2 Docker (Take a certain time)
export ROS_DOMAIN_ID=25
sudo sh ~/script.sh
```
# 2. Create all nodes (Terminal 2)
```bash
export ROS_DOMAIN_ID=25

docker run -it --rm -e ROS_DOMAIN_ID=25 -v /dev:/dev -v /dev/shm:/dev/shm --privileged --net=host microros/micro-ros-agent:humble serial --dev /dev/ttyUSB0 -b 921600 -v4
```
# 3. Create the ROS2 package (Terminal 1, inside ros2 docker)
```bash
export ROS_DOMAIN_ID=25

mkdir -p ~/ros2_ws/src && cd ~/ros2_ws/src

ros2 pkg create --build-type ament_python --node-name ws_control_node ihm_robot --dependencies rclpy std_msgs sensor_msgs geometry_msgs nav_msgs

cd ~/ros2_ws/src/ihm_robot/ihm_robot/

#copy the ws_control_node.py file content, from outside the docker, located at "~/ihm-ros2/robot/ws_control_node.py" into ~/ros2_ws/src/ihm_robot/ihm_robot/ws_control_node.py
# always check for the ethenet IP so the web ip is fine
# Can be checked using this command : 
ip -4 addr show wlan0 | awk '/inet / {print $2}' | cut -d/ -f1
```
# 3. Start camera docker(Terminal 3)
```bash
export ROS_DOMAIN_ID=25
cd ~/ihm-ros2
sudo docker run --rm -it --network=host bluenviron/mediamtx:1
```
# 4.  Start ffmpeg (Terminal 4)
```bash
export ROS_DOMAIN_ID=25
cd ~/ihm-ros2
cat setup
# Take the command: ffmpeg -f v4l2 -s 640x480 -framerate 30 -i /dev/video0   -c:v libx264 -preset veryfast -tune zerolatency   -f rtsp rtsp://localhost:8554/robot 
# run the command in sudo
```
# 4. Start Web server 
```bash
export ROS_DOMAIN_ID=25
cd ~/ihm-ros2
npm run dev
```
# 5. Start the ws_control_node.py
```bash
cd ~/ros2_ws
pip install requests websockets opencv-python mediapipe
colcon build --packages-select ihm_robot
source install/setup.bash
ros2 run ihm_robot ws_control_node
```
