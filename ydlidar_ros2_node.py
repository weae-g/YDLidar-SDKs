#!/usr/bin/env python3
"""
ROS2 node for YDLidar using modern Python bindings (_ydlidar)
Publishes LaserScan messages on /scan
"""
import threading
import time
import os

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import LaserScan
from std_msgs.msg import Header
import tf2_ros
from geometry_msgs.msg import TransformStamped

import ydlidar._ydlidar as yd


class YDLidarRos2Node(Node):
    def __init__(self):
        super().__init__('ydlidar_ros2_node')

        # Parameters
        self.declare_parameter('serial_port', '/dev/ttyUSB0')
        self.declare_parameter('baudrate', 128000)
        self.declare_parameter('frame_id', 'laser')
        self.declare_parameter('topic', '/scan')
        self.declare_parameter('publish_static_tf', True)
        self.declare_parameter('parent_frame', 'base_link')
        self.declare_parameter('use_ros_time', True)

        self.serial_port = self.get_parameter('serial_port').get_parameter_value().string_value
        self.baudrate = self.get_parameter('baudrate').get_parameter_value().integer_value
        self.frame_id = self.get_parameter('frame_id').get_parameter_value().string_value
        self.topic = self.get_parameter('topic').get_parameter_value().string_value
        self.publish_static_tf = self.get_parameter('publish_static_tf').get_parameter_value().bool_value
        self.parent_frame = self.get_parameter('parent_frame').get_parameter_value().string_value
        self.use_ros_time = self.get_parameter('use_ros_time').get_parameter_value().bool_value

        # Publisher
        self.publisher_ = self.create_publisher(LaserScan, self.topic, 10)

        # Initialize YDLidar SDK
        yd.os_init()

        # Set parameters
        yd.setlidaropt(yd.LidarPropSerialPort, self.serial_port)
        yd.setlidaropt(yd.LidarPropSerialBaudrate, self.baudrate)
        try:
            yd.setlidaropt(yd.LidarPropSingleChannel, True)
            yd.setlidaropt(yd.LidarPropIntenstiy, True)
        except Exception:
            pass

        # Check serial port
        if not os.path.exists(self.serial_port):
            self.get_logger().error(f'Serial port does not exist: {self.serial_port}')
            raise RuntimeError(f'Serial port does not exist: {self.serial_port}')
        if not os.access(self.serial_port, os.R_OK | os.W_OK):
            self.get_logger().warning(
                f'No read/write access to {self.serial_port}. '
                'Try: sudo usermod -a -G dialout $USER && newgrp dialout'
            )

        # Initialize device
        if not yd.initialize():
            self.get_logger().error('Failed to initialize YDLidar')
            raise RuntimeError('Failed to initialize YDLidar')

        if not yd.turnOn():
            self.get_logger().error('Failed to turn on YDLidar')
            yd.turnOff()
            raise RuntimeError('Failed to turn on YDLidar')

        # Publish static TF if requested
        if self.publish_static_tf:
            self._tf_broadcaster = tf2_ros.StaticTransformBroadcaster(self)
            t = TransformStamped()
            t.header.stamp = self.get_clock().now().to_msg()
            t.header.frame_id = self.parent_frame
            t.child_frame_id = self.frame_id
            t.transform.translation.x = 0.0
            t.transform.translation.y = 0.0
            t.transform.translation.z = 0.0
            t.transform.rotation.x = 0.0
            t.transform.rotation.y = 0.0
            t.transform.rotation.z = 0.0
            t.transform.rotation.w = 1.0
            self._tf_broadcaster.sendTransform(t)

        # Start reading thread
        self._run_thread = True
        self._thread = threading.Thread(target=self._read_loop, daemon=True)
        self._thread.start()

    def _read_loop(self):
        scan = yd.LaserScan()
        while rclpy.ok() and self._run_thread:
            try:
                if not yd.doProcessSimple(scan):
                    time.sleep(0.01)
                    continue

                # Prepare ROS2 LaserScan message
                header = Header()
                if self.use_ros_time:
                    now = self.get_clock().now().to_msg()
                    header.stamp = now
                else:
                    try:
                        stamp_ns = int(scan.stamp)
                        sec = stamp_ns // 1_000_000_000
                        nanosec = stamp_ns % 1_000_000_000
                        header.stamp.sec = sec
                        header.stamp.nanosec = nanosec
                    except Exception:
                        header.stamp = self.get_clock().now().to_msg()

                header.frame_id = self.frame_id

                cfg = scan.config
                msg = LaserScan()
                msg.header = header
                msg.angle_min = float(cfg.min_angle)
                msg.angle_max = float(cfg.max_angle)
                msg.angle_increment = float(cfg.angle_increment)
                msg.time_increment = float(cfg.time_increment)
                msg.scan_time = float(cfg.scan_time)
                msg.range_min = float(cfg.min_range)
                msg.range_max = float(cfg.max_range)

                npoints = int(scan.points.size())
                ranges = [float('inf')] * npoints
                intensities = [0.0] * npoints
                for i in range(npoints):
                    p = scan.points.__getitem__(i)
                    r = float(p.range)
                    ranges[i] = r if r > 0 else float('inf')
                    intensities[i] = float(getattr(p, 'intensity', 0.0))

                msg.ranges = ranges
                msg.intensities = intensities
                self.publisher_.publish(msg)

            except Exception as e:
                self.get_logger().error(f'Error in read loop: {e}')
                time.sleep(0.1)
        self.get_logger().info('Reader thread terminating')

    def _shutdown(self):
        self._run_thread = False
        try:
            self._thread.join(timeout=1.0)
        except Exception:
            pass
        try:
            yd.turnOff()
        except Exception:
            pass
        try:
            yd.disconnecting()
        except Exception:
            pass
        try:
            yd.os_shutdown()
        except Exception:
            pass


def main(args=None):
    rclpy.init(args=args)
    node = None
    try:
        node = YDLidarRos2Node()
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        if node is not None:
            try:
                node._shutdown()
            except Exception:
                pass
            try:
                node.destroy_node()
            except Exception:
                pass
        rclpy.shutdown()


if __name__ == '__main__':
    main()
