FROM --platform=linux/arm64 ros:humble

# Fix corrupted dpkg files lists (base image has missing newlines)
RUN for f in /var/lib/dpkg/info/*.list; do sed -i -e '$a\' "$f"; done

# Install pip and venv
RUN apt-get update && \
    apt-get install -y --no-install-recommends python3-pip python3-venv

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
