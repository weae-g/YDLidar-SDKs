#!/usr/bin/env python3
"""
ROS2 нода для работы с лидарами YDLidar

Эта нода использует Python bindings от YDLidar SDK для чтения данных
с лидара и публикации их как sensor_msgs/LaserScan в ROS2.

Зависимости: rclpy, sensor_msgs, и модуль ydlidar (собранный из SDK).
Нода использует фоновый поток для чтения данных и публикует каждое сканирование.
"""
import threading
import time
import math
import os
import stat

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import LaserScan
from std_msgs.msg import Header
import tf2_ros
from geometry_msgs.msg import TransformStamped

import ydlidar


class YDLidarRos2Node(Node):
    """ROS2 нода для лидара YDLidar"""
    
    def __init__(self):
        super().__init__('ydlidar_node')
        
        # Объявление параметров ноды
        self.declare_parameter('serial_port', '/dev/ttyUSB0')
        self.declare_parameter('baudrate', 128000)
        self.declare_parameter('frame_id', 'laser')
        self.declare_parameter('topic', '/scan')
        self.declare_parameter('publish_static_tf', True)
        self.declare_parameter('parent_frame', 'base_link')
        self.declare_parameter('use_ros_time', True)

        # Получение значений параметров
        self.serial_port = self.get_parameter('serial_port').get_parameter_value().string_value
        self.baudrate = int(self.get_parameter('baudrate').get_parameter_value().integer_value)
        self.frame_id = self.get_parameter('frame_id').get_parameter_value().string_value
        self.topic = self.get_parameter('topic').get_parameter_value().string_value
        self.publish_static_tf = bool(self.get_parameter('publish_static_tf').get_parameter_value().bool_value)
        self.parent_frame = self.get_parameter('parent_frame').get_parameter_value().string_value
        self.use_ros_time = bool(self.get_parameter('use_ros_time').get_parameter_value().bool_value)

        # Создание publisher для данных лидара
        self.publisher_ = self.create_publisher(LaserScan, self.topic, 10)

        # Инициализация YDLidar SDK
        ydlidar.os_init()
        self.laser = ydlidar.CYdLidar()

        # Настройка подключения к лидару
        self.laser.setlidaropt(ydlidar.LidarPropSerialPort, self.serial_port)
        
        # Попытка установки дополнительных параметров (не все модели поддерживают)
        try:
            self.laser.setlidaropt(ydlidar.LidarPropSingleChannel, True)
            self.laser.setlidaropt(ydlidar.LidarPropIntenstiy, True)
        except Exception:
            # Некоторые версии SDK/аппаратура могут не поддерживать все опции
            pass

        # Проверка существования устройства и разрешений
        if not os.path.exists(self.serial_port):
            self.get_logger().error(f'Последовательный порт не существует: {self.serial_port}')
            raise RuntimeError(f'Последовательный порт не существует: {self.serial_port}')

        # Проверка прав доступа к устройству
        if not os.access(self.serial_port, os.R_OK | os.W_OK):
            self.get_logger().warning(
                f'Нет прав чтения/записи для {self.serial_port}. '
                f'Попробуйте: sudo usermod -a -G dialout $USER && newgrp dialout'
            )

        # Инициализация лидара с различными скоростями передачи данных
        self._initialize_lidar()

        # Публикация статического TF преобразования (если требуется)
        if self.publish_static_tf:
            self._publish_static_transform()

        # Запуск фонового потока для чтения данных
        self._run_thread = True
        self._thread = threading.Thread(target=self._read_loop, daemon=True)
        self._thread.start()

        self.get_logger().info(f'YDLidar нода запущена. Порт: {self.serial_port}, Baudrate: {self.baudrate}')

    def _initialize_lidar(self):
        """Инициализация лидара с перебором возможных скоростей передачи данных"""
        # Список возможных скоростей (начинаем с заданной пользователем)
        baud_candidates = [self.baudrate, 128000, 115200, 230400, 460800, 512000, 153600]
        
        # Удаление дубликатов с сохранением порядка
        seen = set()
        baud_list = []
        for b in baud_candidates:
            if b not in seen and b is not None:
                seen.add(b)
                baud_list.append(int(b))

        initialized = False
        for baudrate in baud_list:
            try:
                self.get_logger().info(f'Попытка инициализации на {self.serial_port} @ {baudrate}')
                self.laser.setlidaropt(ydlidar.LidarPropSerialBaudrate, int(baudrate))
                
                if not self.laser.initialize():
                    self.get_logger().info(f'initialize() вернула False для baudrate {baudrate}')
                    continue
                    
                if not self.laser.turnOn():
                    self.get_logger().info(f'turnOn() вернула False для baudrate {baudrate}')
                    try:
                        self.laser.turnOff()
                    except Exception:
                        pass
                    continue
                    
                initialized = True
                self.baudrate = baudrate  # Обновляем используемую скорость
                self.get_logger().info(f'YDLidar успешно инициализирован на {self.serial_port} @ {baudrate}')
                break
                
            except Exception as e:
                self.get_logger().warning(f'Исключение при попытке baudrate {baudrate}: {str(e)}')
                continue

        if not initialized:
            error_msg = f'Не удалось инициализировать YDLidar на {self.serial_port} с вариантами {baud_list}'
            self.get_logger().error(error_msg)
            raise RuntimeError(error_msg)

    def _publish_static_transform(self):
        """Публикация статического TF преобразования"""
        try:
            self.get_logger().info(f'Публикация статического преобразования {self.parent_frame} -> {self.frame_id}')
            self._tf_broadcaster = tf2_ros.StaticTransformBroadcaster(self)
            
            t = TransformStamped()
            t.header.stamp = self.get_clock().now().to_msg()
            t.header.frame_id = self.parent_frame
            t.child_frame_id = self.frame_id
            
            # Единичное преобразование (лидар в том же месте что и родительская система координат)
            t.transform.translation.x = 0.0
            t.transform.translation.y = 0.0
            t.transform.translation.z = 0.0
            t.transform.rotation.x = 0.0
            t.transform.rotation.y = 0.0
            t.transform.rotation.z = 0.0
            t.transform.rotation.w = 1.0
            
            self._tf_broadcaster.sendTransform(t)
        except Exception as e:
            self.get_logger().warning(f'Не удалось опубликовать статическое TF: {str(e)}')

    def _read_loop(self):
        """Основной цикл чтения данных с лидара"""
        while rclpy.ok() and self._run_thread:
            try:
                scan = ydlidar.LaserScan()
                if not self.laser.doProcessSimple(scan):
                    # Небольшая пауза чтобы избежать busy loop при ошибках
                    time.sleep(0.01)
                    continue

                # Определение времени для штампа сообщения
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
                        # Fallback на текущее время
                        now = self.get_clock().now().to_msg()
                        sec = now.sec
                        nanosec = now.nanosec

                # Создание заголовка сообщения
                header = Header()
                header.stamp.sec = int(sec)
                header.stamp.nanosec = int(nanosec)
                header.frame_id = self.frame_id

                cfg = scan.config

                # Заполнение сообщения LaserScan
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
                
                # Предварительное выделение списков
                ranges = [float('inf')] * npoints
                intensities = [0.0] * npoints

                # Заполнение данных дальности и интенсивности
                for i in range(npoints):
                    p = scan.points.__getitem__(i)
                    
                    # Установка дальности (0 означает отсутствие возврата -> inf)
                    r = float(p.range)
                    if r <= 0.0:
                        ranges[i] = float('inf')
                    else:
                        ranges[i] = r
                    
                    intensities[i] = float(getattr(p, 'intensity', 0.0))

                msg.ranges = ranges
                msg.intensities = intensities

                # Публикация сообщения
                self.publisher_.publish(msg)
                
            except Exception as e:
                self.get_logger().error(f'Ошибка в цикле чтения: {str(e)}')
                time.sleep(0.1)

        self.get_logger().info('Поток чтения завершается')

    def shutdown(self):
        """Корректное завершение работы ноды"""
        self.get_logger().info('Завершение работы YDLidar ноды')
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
    """Главная функция для запуска ноды"""
    rclpy.init(args=args)
    node = None
    
    try:
        node = YDLidarRos2Node()
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    except Exception as e:
        if node:
            node.get_logger().error(f'Критическая ошибка: {str(e)}')
        else:
            print(f'Критическая ошибка при инициализации: {str(e)}')
    finally:
        # Корректное завершение работы лидара перед уничтожением ноды
        if node is not None:
            try:
                node.shutdown()
            except Exception:
                pass
            try:
                node.destroy_node()
            except Exception:
                pass
        rclpy.shutdown()


if __name__ == '__main__':
    main()