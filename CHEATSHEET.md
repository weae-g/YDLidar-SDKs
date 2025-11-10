# 🚀 YDLidar Quick Reference - Шпаргалка

## Быстрый запуск

```bash
cd /home/weae/weae/YDLidar-SDKs
./start_ydlidar.sh
```

---

## 📝 Доступные ноды

| Нода | Описание | Когда использовать |
|------|----------|-------------------|
| `ydlidar_ros2_node.py` | Полная версия с оптимизацией | Production, RViz2 на ПК ⭐ |
| `ydlidar_ros2_simple.py` | Упрощенная без turnOn() | Отладка, проблемы с turnOn() |
| `start_ydlidar.sh` | Скрипт быстрого запуска | Рекомендуется для всех |

---

## 🎯 Команды запуска

### Скрипт (Рекомендуется)
```bash
./start_ydlidar.sh                    # Автопоиск, оптимальные настройки
./start_ydlidar.sh auto 2 720         # То же самое (явно)
./start_ydlidar.sh auto 4 360         # Слабый ПК
./start_ydlidar.sh /dev/ttyUSB1 2 720 # Указать порт
```

### Основная нода
```bash
./ydlidar_ros2_node.py                # Автопоиск + умолчания
./ydlidar_ros2_node.py --ros-args \
  -p serial_port:=auto \
  -p downsample_factor:=2 \
  -p max_points:=720
```

### Упрощенная нода
```bash
./ydlidar_ros2_simple.py              # Автопоиск + умолчания
./ydlidar_ros2_simple.py --ros-args \
  -p serial_port:=/dev/ttyUSB1 \
  -p single_channel:=true
```

---

## 📊 Параметры start_ydlidar.sh

```bash
./start_ydlidar.sh [port] [downsample] [max_points]
```

| Позиция | Параметр | По умолчанию | Значения |
|---------|----------|--------------|----------|
| 1 | port | `auto` | `auto`, `/dev/ttyUSB0`, `/dev/ttyUSB1` |
| 2 | downsample | `2` | `1` (нет), `2` (½), `3` (⅓), `4` (¼) |
| 3 | max_points | `720` | `0` (нет), `360`, `720`, `1260` |

---

## 🔧 Параметры ydlidar_ros2_node.py

| Параметр | Умолчание | Описание |
|----------|-----------|----------|
| `serial_port` | `auto` | Порт или 'auto' |
| `baudrate` | `128000` | 115200, 128000, 230400, 512000 |
| `frame_id` | `laser` | ID фрейма |
| `topic` | `/scan` | Топик публикации |
| `publish_static_tf` | `true` | Публиковать TF |
| `parent_frame` | `base_link` | Родительский фрейм |
| `use_ros_time` | `true` | Использовать ROS время |
| `downsample_factor` | `2` | Коэфф. прореживания |
| `max_points` | `720` | Макс. точек в скане |

---

## 🔧 Параметры ydlidar_ros2_simple.py

| Параметр | Умолчание | Описание |
|----------|-----------|----------|
| `serial_port` | `auto` | Порт или 'auto' |
| `baudrate` | `128000` | Скорость |
| `frame_id` | `laser` | ID фрейма |
| `topic` | `/scan` | Топик |
| `publish_static_tf` | `true` | TF |
| `parent_frame` | `base_link` | Родительский фрейм |
| `single_channel` | `true` | Односторонняя связь (T1) |
| `lidar_type` | `1` | 1=Triangle, 2=TOF |

---

## ⚙️ Режимы прореживания

| downsample | Точек | Описание | Применение |
|------------|-------|----------|------------|
| `1` | ~1260 | Без прореживания | Точные измерения, мощный ПК |
| `2` | ~630 | Каждая 2-я | **Рекомендуется** ⭐ |
| `3` | ~420 | Каждая 3-я | Слабый ПК |
| `4` | ~315 | Каждая 4-я | Очень слабый ПК |

---

## 🛠️ Проверка работы

```bash
# Топики
ros2 topic list
ros2 topic hz /scan
ros2 topic echo /scan --once

# Нода
ros2 node list
ros2 node info /ydlidar_ros2_node

# Параметры
ros2 param list /ydlidar_ros2_node
ros2 param get /ydlidar_ros2_node downsample_factor
```

---

## 🐛 Быстрое решение проблем

| Проблема | Решение |
|----------|---------|
| "No YDLidar device found" | `ls -l /dev/ttyUSB*` → укажите порт явно |
| "Permission denied" | `sudo usermod -a -G dialout $USER; newgrp dialout` |
| "turnOn() returned False" | Используйте `ydlidar_ros2_simple.py` |
| RViz2 вылетает | `./start_ydlidar.sh auto 4 360` |
| "No module named ydlidar" | `export PYTHONPATH=/usr/local/lib/python3/dist-packages:$PYTHONPATH` |

---

## 📍 Пути и файлы

```bash
SDK:              /usr/local/lib/libydlidar_sdk.a
Python модуль:    /usr/local/lib/python3/dist-packages/ydlidar.py
Ноды:             /home/weae/weae/YDLidar-SDKs/ydlidar_ros2_*.py
Скрипт запуска:   /home/weae/weae/YDLidar-SDKs/start_ydlidar.sh
Сервис:           /etc/systemd/system/ydlidar.service
```

---

## 🎓 Примеры для разных случаев

### T1 на Raspberry Pi + RViz на ПК
```bash
./start_ydlidar.sh auto 2 720
```

### Слабая система
```bash
./start_ydlidar.sh auto 4 360
```

### Известный порт
```bash
./start_ydlidar.sh /dev/ttyUSB1
```

### Проблемы с turnOn()
```bash
./ydlidar_ros2_simple.py
```

### Максимальная точность (мощный ПК)
```bash
./ydlidar_ros2_simple.py --ros-args -p serial_port:=/dev/ttyUSB1
```

---

## 🔄 Systemd сервис

```bash
# Управление
sudo systemctl start ydlidar
sudo systemctl stop ydlidar
sudo systemctl restart ydlidar
sudo systemctl status ydlidar

# Автозапуск
sudo systemctl enable ydlidar   # Включить
sudo systemctl disable ydlidar  # Выключить

# Логи
journalctl -u ydlidar -f
journalctl -u ydlidar --since "5 minutes ago"
```

---

## 📚 Документация

- `INSTALLATION_GUIDE_RPI5.md` - Полная установка
- `QUICK_START.md` - Быстрый старт
- `AUTO_DETECTION.md` - Автопоиск устройств
- `SUMMARY.md` - Общая сводка

---

**Версия:** 2.0  
**Дата:** 10 ноября 2025  
**Платформа:** Raspberry Pi 5 + ROS2 Jazzy
