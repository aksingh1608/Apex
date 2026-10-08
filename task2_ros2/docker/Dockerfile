FROM osrf/ros:humble-desktop-full

ENV DEBIAN_FRONTEND=noninteractive
ENV TURTLEBOT3_MODEL=burger

RUN apt-get update && apt-get install -y --no-install-recommends \
        ros-humble-turtlebot3 \
        ros-humble-turtlebot3-gazebo \
        ros-humble-gazebo-ros-pkgs \
        python3-matplotlib \
        python3-yaml \
        python3-pytest \
    && rm -rf /var/lib/apt/lists/*

RUN mkdir -p /ws/src && chmod 777 /ws
WORKDIR /ws

COPY apex_env.sh /opt/apex_env.sh
COPY entrypoint.sh /opt/entrypoint.sh
RUN chmod +x /opt/apex_env.sh /opt/entrypoint.sh

ENTRYPOINT ["/opt/entrypoint.sh"]
CMD ["bash"]
