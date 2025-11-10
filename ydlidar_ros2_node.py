#!/usr/bin/env python3
"""
ROS2 node that uses YDLidar SDK Python bindings to read scans from a LiDAR
and publish them as sensor_msgs/LaserScan on the /scan topic.

Dependencies: rclpy, sensor_msgs, and the ydlidar Python bindings built from
this SDK (the package name is `ydlidar` as produced by the SDK build).

This script uses blocking reads in a background thread and publishes each
successful scan.
Features auto-detection of LiDAR device and data downsampling.
"""
import threading
import time
import math
import os
import stat
import glob
import subprocess

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import LaserScan
from std_msgs.msg import Header
import tf2_ros
from geometry_msgs.msg import TransformStamped

import ydlidar


def find_ydlidar_port():
    """
    Automatically find YDLidar USB port.
    Returns the port path or None if not found.
    """
    # Check common USB serial ports
    potential_ports = []
    
    # Search for ttyUSB* devices
    potential_ports.extend(glob.glob('/dev/ttyUSB*'))
    
    # Search for ttyACM* devices
    potential_ports.extend(glob.glob('/dev/ttyACM*'))
    
    if not potential_ports:
        return None
    
    # Try to identify YDLidar by checking device info
    for port in sorted(potential_ports):
        try:
            # Check if we can access the port
            if not os.access(port, os.R_OK | os.W_OK):
                continue
                
            # Try to get device info using udevadm
            try:
                result = subprocess.run(
                    ['udevadm', 'info', '-a', '-n', port],
                    capture_output=True,
                    text=True,
                    timeout=2
                )
                device_info = result.stdout.lower()
                
                # Look for YDLidar identifiers
                # CP2102 is common USB-UART chip used in YDLidar devices
                if any(keyword in device_info for keyword in ['cp210', 'ydlidar', '10c4:ea60']):
                    return port
            except (subprocess.TimeoutExpired, FileNotFoundError):
                pass
            
        except Exception:
            continue
    
    # If no specific YDLidar found, return first available port
    for port in sorted(potential_ports):
        if os.access(port, os.R_OK | os.W_OK):
            return port
    
    return None


class YDLidarRos2Node(Node):
    def __init__(self):
        super().__init__('ydlidar_ros2_node')
        # parameters (can be remapped via ROS2 params or CLI)
        self.declare_parameter('serial_port', 'auto')  # 'auto' for auto-detection or specify like '/dev/ttyUSB1'
        self.declare_parameter('baudrate', 128000)
        self.declare_parameter('frame_id', 'laser')
        self.declare_parameter('topic', '/scan')
        # publish static tf from parent_frame -> frame_id (so RViz won't drop messages)
        self.declare_parameter('publish_static_tf', True)
        self.declare_parameter('parent_frame', 'base_link')
        # whether to use ROS time for message header.stamp (recommended True)
        self.declare_parameter('use_ros_time', True)
        # Downsampling factor to reduce point cloud size (1 = no downsampling, 2 = every 2nd point, etc.)
        self.declare_parameter('downsample_factor', 2)
        # Maximum number of points per scan (0 = no limit)
        self.declare_parameter('max_points', 720)

        serial_port_param = self.get_parameter('serial_port').get_parameter_value().string_value
        self.baudrate = int(self.get_parameter('baudrate').get_parameter_value().integer_value)
        self.frame_id = self.get_parameter('frame_id').get_parameter_value().string_value
        self.topic = self.get_parameter('topic').get_parameter_value().string_value
        self.publish_static_tf = bool(self.get_parameter('publish_static_tf').get_parameter_value().bool_value)
        self.parent_frame = self.get_parameter('parent_frame').get_parameter_value().string_value
        self.use_ros_time = bool(self.get_parameter('use_ros_time').get_parameter_value().bool_value)
        self.downsample_factor = int(self.get_parameter('downsample_factor').get_parameter_value().integer_value)
        self.max_points = int(self.get_parameter('max_points').get_parameter_value().integer_value)

        # Auto-detect serial port if set to 'auto'
        if serial_port_param == 'auto':
            self.get_logger().info('Auto-detecting YDLidar device...')
            self.serial_port = find_ydlidar_port()
            if self.serial_port:
                self.get_logger().info('Found YDLidar at: %s' % self.serial_port)
            else:
                self.get_logger().error('No YDLidar device found!')
                available = glob.glob('/dev/ttyUSB*') + glob.glob('/dev/ttyACM*')
                self.get_logger().error('Available ports: %s' % str(available))
                raise RuntimeError('YDLidar device not found')
        else:
            self.serial_port = serial_port_param
            self.get_logger().info('Using specified port: %s' % self.serial_port)

        self.publisher_ = self.create_publisher(LaserScan, self.topic, 10)

        # Initialize ydlidar SDK
        ydlidar.os_init()
        self.laser = ydlidar.CYdLidar()

        # Configure lidar connection
        self.laser.setlidaropt(ydlidar.LidarPropSerialPort, self.serial_port)
        # T1 is single channel (one-way communication)
        try:
            self.laser.setlidaropt(ydlidar.LidarPropSingleChannel, True)
            self.laser.setlidaropt(ydlidar.LidarPropIntenstiy, False)
            self.laser.setlidaropt(ydlidar.LidarPropAutoReconnect, True)
            self.laser.setlidaropt(ydlidar.LidarPropMaxRange, 16.0)
            self.laser.setlidaropt(ydlidar.LidarPropMinRange, 0.12)
            self.laser.setlidaropt(ydlidar.LidarPropMaxAngle, 180.0)
            self.laser.setlidaropt(ydlidar.LidarPropMinAngle, -180.0)
            self.laser.setlidaropt(ydlidar.LidarPropScanFrequency, 6.0)
            self.laser.setlidaropt(ydlidar.LidarPropFixedResolution, True)
            self.laser.setlidaropt(ydlidar.LidarPropReversion, False)
            self.laser.setlidaropt(ydlidar.LidarPropInverted, False)
            self.laser.setlidaropt(ydlidar.LidarPropLidarType, 1)  # TYPE_TRIANGLE
            self.laser.setlidaropt(ydlidar.LidarPropDeviceType, 0)
            self.laser.setlidaropt(ydlidar.LidarPropSampleRate, 5)  # 5K
        except Exception as e:
            # some bindings/hardware may not support every option; ignore safely
            self.get_logger().warning('Some LiDAR options not set: %s' % str(e))

        # Quick diagnostics: check device exists and permissions
        if not os.path.exists(self.serial_port):
            self.get_logger().error('Serial port does not exist: %s' % self.serial_port)
            raise RuntimeError('Serial port does not exist: %s' % self.serial_port)

        # Check read/write permission to device
        if not os.access(self.serial_port, os.R_OK | os.W_OK):
            # common fix: add user to dialout group
            self.get_logger().warning('No read/write access to %s. Try: sudo usermod -a -G dialout $USER && newgrp dialout' % self.serial_port)

        # Try the configured baudrate first, then a list of common options
        baud_candidates = [self.baudrate, 128000, 115200, 230400, 460800, 512000, 153600]
        # de-duplicate while preserving order
        seen = set()
        baud_list = []
        for b in baud_candidates:
            if b not in seen and b is not None:
                seen.add(b)
                baud_list.append(int(b))

        initialized = False
        for b in baud_list:
            try:
                self.get_logger().info('Attempting init on %s @ %d' % (self.serial_port, b))
                self.laser.setlidaropt(ydlidar.LidarPropSerialBaudrate, int(b))
                ok = self.laser.initialize()
                if not ok:
                    self.get_logger().info('initialize() returned False for baud %d' % b)
                    continue
                
                # Give the lidar a moment to stabilize after initialization
                time.sleep(0.2)
                
                ok = self.laser.turnOn()
                if not ok:
                    self.get_logger().warning('turnOn() returned False for baud %d' % b)
                    # If initialize succeeded but turnOn failed, properly disconnect before retrying
                    try:
                        self.laser.turnOff()
                        self.laser.disconnecting()
                        time.sleep(0.5)
                    except Exception:
                        pass
                    continue
                initialized = True
                self.get_logger().info('Initialized YDLidar on %s @ %d' % (self.serial_port, b))
                break
            except Exception as e:
                self.get_logger().warning('Exception while trying baud %d: %s' % (b, str(e)))
                # Clean up before trying next baudrate
                try:
                    self.laser.disconnecting()
                    time.sleep(0.3)
                except Exception:
                    pass
                continue

        if not initialized:
            self.get_logger().error('Failed to initialize YDLidar on %s with candidates %s' % (self.serial_port, baud_list))
            raise RuntimeError('Failed to initialize YDLidar')

        # publish static transform if requested so RViz has the TF immediately
        if self.publish_static_tf:
            try:
                self.get_logger().info('Publishing static transform %s -> %s' % (self.parent_frame, self.frame_id))
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
            except Exception as e:
                self.get_logger().warning('Failed to publish static TF: %s' % str(e))

        # background thread that reads scans and publishes them
        self._run_thread = True
        self._thread = threading.Thread(target=self._read_loop, daemon=True)
        self._thread.start()

    # ensure clean shutdown handled by the caller (main)

    def _read_loop(self):
        scan_msg = LaserScan()
        while rclpy.ok() and self._run_thread:
            try:
                scan = ydlidar.LaserScan()
                ok = self.laser.doProcessSimple(scan)
                if not ok:
                    # small sleep to avoid busy loop on failure
                    time.sleep(0.01)
                    continue

                # stamp: use ROS time if configured, otherwise try SDK stamp (ns)
                if self.use_ros_time:
                    now = self.get_clock().now().to_msg()
                    sec = now.sec
                    nanosec = now.nanosec
                else:
                    try:
                        stamp_ns = int(scan.stamp)
                        sec = stamp_ns // 1000000000
                        nanosec = stamp_ns % 1000000000
                    except Exception:
                        # fallback to current time
                        now = self.get_clock().now().to_msg()
                        sec = now.sec
                        nanosec = now.nanosec

                header = Header()
                header.stamp.sec = int(sec)
                header.stamp.nanosec = int(nanosec)
                header.frame_id = self.frame_id

                cfg = scan.config

                # Fill LaserScan fields
                msg = LaserScan()
                msg.header = header
                # The YDLidar LaserConfig fields are expected to be in radians and seconds
                msg.angle_min = float(cfg.min_angle)
                msg.angle_max = float(cfg.max_angle)
                msg.angle_increment = float(cfg.angle_increment)
                msg.time_increment = float(cfg.time_increment)
                msg.scan_time = float(cfg.scan_time)
                msg.range_min = float(cfg.min_range)
                msg.range_max = float(cfg.max_range)

                npoints = int(scan.points.size())
                
                # Apply downsampling and max points limit
                step = max(1, self.downsample_factor)
                if self.max_points > 0 and npoints > self.max_points:
                    # Calculate step to fit within max_points
                    step = max(step, int(npoints / self.max_points))
                
                # Calculate actual number of points after downsampling
                actual_points = (npoints + step - 1) // step
                
                # Preallocate lists with downsampled size
                ranges = [float('inf')] * actual_points
                intensities = [0.0] * actual_points

                # Fill ranges/intensities with downsampling
                out_idx = 0
                for i in range(0, npoints, step):
                    if out_idx >= actual_points:
                        break
                    p = scan.points.__getitem__(i)
                    # p.range may be 0 for no return; set to inf to match ROS conventions
                    r = float(p.range)
                    if r <= 0.0:
                        ranges[out_idx] = float('inf')
                    else:
                        ranges[out_idx] = r
                    intensities[out_idx] = float(getattr(p, 'intensity', 0.0))
                    out_idx += 1
                
                # Adjust angle_increment for downsampling
                msg.angle_increment = float(cfg.angle_increment) * step

                msg.ranges = ranges
                msg.intensities = intensities

                # publish
                self.publisher_.publish(msg)
            except Exception as e:
                self.get_logger().error('Error in read loop: %s' % str(e))
                time.sleep(0.1)

        self.get_logger().info('Reader thread terminating')

    def _shutdown(self):
        self.get_logger().info('Shutting down YDLidar node')
        self._run_thread = False
        try:
            self._thread.join(timeout=1.0)
        except Exception:
            pass
        try:
            self.laser.turnOff()
        except Exception:
            pass
        try:
            self.laser.disconnecting()
        except Exception:
            pass
        try:
            ydlidar.os_shutdown()
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
        # Stop reader thread and cleanly shutdown the lidar before destroying the node
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
