#!/usr/bin/env python3
"""
Simplified YDLidar ROS2 node for TOF/Triangle series LiDARs.
This version uses simpler initialization without turnOn() call.
Features auto-detection of LiDAR device.
"""
import threading
import time
import os
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


class YDLidarSimpleNode(Node):
    def __init__(self):
        super().__init__('ydlidar_simple_node')
        
        # Declare parameters
        self.declare_parameter('serial_port', 'auto')  # 'auto' for auto-detection
        self.declare_parameter('baudrate', 128000)
        self.declare_parameter('frame_id', 'laser')
        self.declare_parameter('topic', '/scan')
        self.declare_parameter('publish_static_tf', True)
        self.declare_parameter('parent_frame', 'base_link')
        self.declare_parameter('single_channel', True)  # T1 is single channel
        self.declare_parameter('lidar_type', 1)  # TYPE_TRIANGLE = 1, TYPE_TOF = 2

        # Get parameters
        serial_port_param = self.get_parameter('serial_port').value
        self.baudrate = self.get_parameter('baudrate').value
        self.frame_id = self.get_parameter('frame_id').value
        self.topic = self.get_parameter('topic').value
        self.publish_static_tf = self.get_parameter('publish_static_tf').value
        self.parent_frame = self.get_parameter('parent_frame').value
        self.single_channel = self.get_parameter('single_channel').value
        self.lidar_type = self.get_parameter('lidar_type').value

        # Auto-detect serial port if set to 'auto'
        if serial_port_param == 'auto':
            self.get_logger().info('Auto-detecting YDLidar device...')
            self.serial_port = find_ydlidar_port()
            if self.serial_port:
                self.get_logger().info('Found YDLidar at: %s' % self.serial_port)
            else:
                self.get_logger().error('No YDLidar device found!')
                self.get_logger().error('Available ports: %s' % str(glob.glob('/dev/ttyUSB*') + glob.glob('/dev/ttyACM*')))
                raise RuntimeError('YDLidar device not found')
        else:
            self.serial_port = serial_port_param
            self.get_logger().info('Using specified port: %s' % self.serial_port)

        self.publisher_ = self.create_publisher(LaserScan, self.topic, 10)

        # Initialize SDK
        ydlidar.os_init()
        self.laser = ydlidar.CYdLidar()

        # Basic configuration
        self.laser.setlidaropt(ydlidar.LidarPropSerialPort, self.serial_port)
        self.laser.setlidaropt(ydlidar.LidarPropSerialBaudrate, self.baudrate)
        self.laser.setlidaropt(ydlidar.LidarPropLidarType, self.lidar_type)
        self.laser.setlidaropt(ydlidar.LidarPropDeviceType, 0)
        self.laser.setlidaropt(ydlidar.LidarPropSampleRate, 5)  # 5K for T1
        self.laser.setlidaropt(ydlidar.LidarPropSingleChannel, self.single_channel)
        
        # Range and angle settings
        self.laser.setlidaropt(ydlidar.LidarPropMaxRange, 16.0)  # T1 max range
        self.laser.setlidaropt(ydlidar.LidarPropMinRange, 0.12)  # T1 min range
        self.laser.setlidaropt(ydlidar.LidarPropMaxAngle, 180.0)
        self.laser.setlidaropt(ydlidar.LidarPropMinAngle, -180.0)
        
        # Scan frequency
        self.laser.setlidaropt(ydlidar.LidarPropScanFrequency, 6.0)  # T1 typical freq
        
        # Additional options for T1
        try:
            self.laser.setlidaropt(ydlidar.LidarPropIntenstiy, False)
            self.laser.setlidaropt(ydlidar.LidarPropAutoReconnect, True)
            self.laser.setlidaropt(ydlidar.LidarPropFixedResolution, True)  # T1 has fixed resolution
            self.laser.setlidaropt(ydlidar.LidarPropReversion, False)
            self.laser.setlidaropt(ydlidar.LidarPropInverted, False)  # Changed to False for T1
        except Exception as e:
            self.get_logger().warning('Optional settings: %s' % str(e))

        # Check device
        if not os.path.exists(self.serial_port):
            self.get_logger().error('Serial port does not exist: %s' % self.serial_port)
            raise RuntimeError('Serial port does not exist')

        if not os.access(self.serial_port, os.R_OK | os.W_OK):
            self.get_logger().warning('No access to %s. Add user to dialout group!' % self.serial_port)

        # Initialize LiDAR
        self.get_logger().info('Initializing LiDAR on %s @ %d...' % (self.serial_port, self.baudrate))
        ret = self.laser.initialize()
        if not ret:
            self.get_logger().error('Failed to initialize LiDAR')
            raise RuntimeError('LiDAR initialization failed')

        self.get_logger().info('LiDAR initialized successfully')

        # Publish static TF
        if self.publish_static_tf:
            try:
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
                self.get_logger().info('Published static TF: %s -> %s' % (self.parent_frame, self.frame_id))
            except Exception as e:
                self.get_logger().warning('TF error: %s' % str(e))

        # Start scanning thread
        self._run_thread = True
        self._thread = threading.Thread(target=self._scan_loop, daemon=True)
        self._thread.start()
        self.get_logger().info('YDLidar node started, publishing to %s' % self.topic)

    def _scan_loop(self):
        """Main scanning loop"""
        while rclpy.ok() and self._run_thread:
            try:
                scan = ydlidar.LaserScan()
                ret = self.laser.doProcessSimple(scan)
                
                if not ret:
                    time.sleep(0.01)
                    continue

                # Create ROS message
                msg = LaserScan()
                msg.header.stamp = self.get_clock().now().to_msg()
                msg.header.frame_id = self.frame_id

                # Get config
                cfg = scan.config
                msg.angle_min = float(cfg.min_angle)
                msg.angle_max = float(cfg.max_angle)
                msg.angle_increment = float(cfg.angle_increment)
                msg.time_increment = float(cfg.time_increment)
                msg.scan_time = float(cfg.scan_time)
                msg.range_min = float(cfg.min_range)
                msg.range_max = float(cfg.max_range)

                # Get points
                npoints = int(scan.points.size())
                ranges = [float('inf')] * npoints
                intensities = [0.0] * npoints

                for i in range(npoints):
                    p = scan.points[i]
                    r = float(p.range)
                    ranges[i] = r if r > 0.0 else float('inf')
                    intensities[i] = float(getattr(p, 'intensity', 0.0))

                msg.ranges = ranges
                msg.intensities = intensities

                # Publish
                self.publisher_.publish(msg)

            except Exception as e:
                self.get_logger().error('Scan error: %s' % str(e))
                time.sleep(0.1)

        self.get_logger().info('Scan thread stopped')

    def shutdown(self):
        """Clean shutdown"""
        self.get_logger().info('Shutting down...')
        self._run_thread = False
        try:
            self._thread.join(timeout=1.0)
        except:
            pass
        try:
            self.laser.turnOff()
        except:
            pass
        try:
            self.laser.disconnecting()
        except:
            pass
        try:
            ydlidar.os_shutdown()
        except:
            pass


def main(args=None):
    rclpy.init(args=args)
    node = None
    try:
        node = YDLidarSimpleNode()
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    except Exception as e:
        print('Error: %s' % str(e))
    finally:
        if node is not None:
            try:
                node.shutdown()
            except:
                pass
            try:
                node.destroy_node()
            except:
                pass
        rclpy.shutdown()


if __name__ == '__main__':
    main()
