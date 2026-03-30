FROM ros:humble

# Fix corrupted dpkg state, then install pip and venv support
RUN apt-get update && \
    apt-get install -y --no-install-recommends python3-pip python3-venv && \
    rm -rf /var/lib/apt/lists/*

# Create a virtual env with access to system packages (rclpy, sensor_msgs, etc.)
RUN python3 -m venv --system-site-packages /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Install pip dependencies
COPY requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt && rm /tmp/requirements.txt

# Copy all node scripts
WORKDIR /app
COPY . /app/

# Custom entrypoint: source ROS2 + activate venv
COPY ros_entrypoint.sh /ros_entrypoint.sh
RUN chmod +x /ros_entrypoint.sh
ENTRYPOINT ["/ros_entrypoint.sh"]

# Default: telemetry node (override via docker-compose for other nodes)
CMD ["python3", "telemetry_node.py"]
