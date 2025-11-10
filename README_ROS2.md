# YDLidar SDK для ROS2 Jazzy

> Оптимизированная реализация YDLidar SDK для ROS2 с автопоиском устройств и прореживанием данных

[![ROS2](https://img.shields.io/badge/ROS2-Jazzy-blue)](https://docs.ros.org/en/jazzy/)
[![Platform](https://img.shields.io/badge/Platform-Raspberry%20Pi%205-red)](https://www.raspberrypi.com/)
[![Ubuntu](https://img.shields.io/badge/Ubuntu-24.04-orange)](https://ubuntu.com/)
[![LiDAR](https://img.shields.io/badge/LiDAR-YDLidar%20T1-green)](http://www.ydlidar.com/)

---

## ✨ Основные возможности

- 🔍 **Автоматический поиск устройства** - не нужно указывать порт вручную
- 🎯 **Прореживание данных** - оптимизация для RViz2 и слабых систем
- 🚀 **Простой запуск** - один скрипт для всех настроек
- 🔄 **Автоперебор baudrate** - автоматический подбор скорости
- 📊 **Две ноды на выбор** - полная и упрощенная версии
- 🛡️ **Стабильная работа** - проверено на Raspberry Pi 5 и ПК

---

## 🚀 Быстрый старт

```bash
# 1. Клонирование репозитория (если ещё не сделано)
cd /home/weae/weae
git clone https://github.com/weae-g/YDLidar-SDKs.git
cd YDLidar-SDKs

# 2. Установка SDK (один раз)
mkdir -p build && cd build
cmake .. && make -j$(nproc)
sudo make install

# 3. Настройка окружения (один раз)
cd ..
chmod +x setup.sh
./setup.sh

# 4. Запуск!
./start_ydlidar.sh
```

**Готово!** Ваш LiDAR работает и публикует данные в топик `/scan`

---

## 📦 Структура проекта

```
YDLidar-SDKs/
├── ydlidar_ros2_node.py          # Основная нода (с оптимизацией)
├── ydlidar_ros2_simple.py        # Упрощенная нода (без turnOn)
├── start_ydlidar.sh              # Скрипт быстрого запуска
├── setup.sh                      # Настройка окружения
├── launch_ydlidar.py             # ROS2 launch файл
│
├── INSTALLATION_GUIDE_RPI5.md    # 📖 Полная инструкция
├── QUICK_START.md                # ⚡ Быстрый старт
├── AUTO_DETECTION.md             # 🔍 Автопоиск устройств
├── SUMMARY.md                    # 📝 Общая сводка
└── CHEATSHEET.md                 # 🎯 Шпаргалка
```

---

## 📖 Документация

| Документ | Описание | Для кого |
|----------|----------|----------|
| [INSTALLATION_GUIDE_RPI5.md](INSTALLATION_GUIDE_RPI5.md) | Полная инструкция по установке | Новички |
| [QUICK_START.md](QUICK_START.md) | Краткое руководство | Опытные пользователи |
| [AUTO_DETECTION.md](AUTO_DETECTION.md) | Автопоиск устройств | Все |
| [CHEATSHEET.md](CHEATSHEET.md) | Быстрая справка | Все |
| [SUMMARY.md](SUMMARY.md) | Итоговая сводка | Все |

---

## 🎯 Доступные ноды

### 1. `ydlidar_ros2_node.py` - Полная версия ⭐

**Возможности:**
- ✅ Автопоиск устройства
- ✅ Прореживание данных (downsample)
- ✅ Ограничение точек (max_points)
- ✅ Автоперебор baudrate
- ✅ 9 настраиваемых параметров

**Когда использовать:**
- Production окружение
- Визуализация в RViz2 на ПК
- Слабые системы (с прореживанием)

**Запуск:**
```bash
./ydlidar_ros2_node.py
```

### 2. `ydlidar_ros2_simple.py` - Упрощенная версия

**Возможности:**
- ✅ Автопоиск устройства
- ✅ Простая инициализация (без turnOn)
- ✅ 8 параметров
- ❌ Без прореживания
- ❌ Без автоперебора baudrate

**Когда использовать:**
- Отладка и тестирование
- Проблемы с turnOn()
- Максимальная точность на мощных ПК

**Запуск:**
```bash
./ydlidar_ros2_simple.py
```

### 3. `start_ydlidar.sh` - Скрипт запуска

**Самый простой способ!**

```bash
./start_ydlidar.sh [port] [downsample] [max_points]
```

**Примеры:**
```bash
./start_ydlidar.sh                    # Автопоиск, оптимально
./start_ydlidar.sh auto 2 720         # То же самое (явно)
./start_ydlidar.sh auto 4 360         # Для слабых ПК
./start_ydlidar.sh /dev/ttyUSB1 2 720 # Указать порт
```

---

## ⚙️ Параметры и настройки

### Параметры `ydlidar_ros2_node.py`

| Параметр | Тип | Умолчание | Описание |
|----------|-----|-----------|----------|
| `serial_port` | string | `auto` | Порт или 'auto' для автопоиска |
| `baudrate` | int | `128000` | Скорость (115200/128000/230400/512000) |
| `frame_id` | string | `laser` | ID фрейма LaserScan |
| `topic` | string | `/scan` | Топик публикации |
| `publish_static_tf` | bool | `true` | Публиковать TF |
| `parent_frame` | string | `base_link` | Родительский фрейм |
| `use_ros_time` | bool | `true` | Использовать ROS время |
| `downsample_factor` | int | `2` | Прореживание (1/2/3/4) |
| `max_points` | int | `720` | Макс. точек (0=нет лимита) |

### Режимы прореживания

| Коэффициент | Точек | Нагрузка | Применение |
|-------------|-------|----------|------------|
| 1 | ~1260 | Высокая | Точные измерения |
| 2 | ~630 | Средняя | **Рекомендуется** ⭐ |
| 3 | ~420 | Низкая | Слабый ПК |
| 4 | ~315 | Минимальная | Очень слабый ПК |

---

## 💡 Примеры использования

### Для YDLidar T1 (по умолчанию)
```bash
./start_ydlidar.sh auto 2 720
```

### Слабая система (Raspberry Pi 3/4)
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

### Максимальная точность
```bash
./ydlidar_ros2_simple.py --ros-args -p serial_port:=/dev/ttyUSB1
```

### С кастомными параметрами
```bash
./ydlidar_ros2_node.py --ros-args \
  -p serial_port:=auto \
  -p baudrate:=128000 \
  -p downsample_factor:=3 \
  -p max_points:=600 \
  -p frame_id:=lidar_frame
```

---

## 🔧 Установка

### Системные требования

- Ubuntu 24.04 (или совместимая)
- ROS2 Jazzy
- Python 3.12+
- CMake 3.5+
- GCC/G++

### Шаг 1: Установка зависимостей

```bash
sudo apt update
sudo apt install -y cmake pkg-config git build-essential
sudo apt install -y python3 python3-pip swig
sudo apt install -y python3-rclpy python3-sensor-msgs python3-tf2-ros
```

### Шаг 2: Сборка SDK

```bash
cd YDLidar-SDKs
mkdir -p build && cd build
cmake ..
make -j$(nproc)
sudo make install
```

### Шаг 3: Настройка Python

```bash
export PYTHONPATH=/usr/local/lib/python3/dist-packages:$PYTHONPATH
echo 'export PYTHONPATH=/usr/local/lib/python3/dist-packages:$PYTHONPATH' >> ~/.bashrc
```

### Шаг 4: Права доступа

```bash
sudo usermod -a -G dialout $USER
newgrp dialout
```

### Шаг 5: Проверка

```bash
python3 -c "import ydlidar; print('OK')"
./start_ydlidar.sh
```

**Подробнее:** [INSTALLATION_GUIDE_RPI5.md](INSTALLATION_GUIDE_RPI5.md)

---

## 🐛 Решение проблем

| Проблема | Решение |
|----------|---------|
| "No YDLidar device found" | Проверьте подключение: `ls -l /dev/ttyUSB*` |
| "Permission denied" | Добавьте в группу: `sudo usermod -a -G dialout $USER` |
| "turnOn() returned False" | Используйте: `./ydlidar_ros2_simple.py` |
| RViz2 вылетает | Прореживание: `./start_ydlidar.sh auto 4 360` |
| "Module not found" | Экспорт: `export PYTHONPATH=/usr/local/lib/python3/dist-packages:$PYTHONPATH` |

**Подробнее:** [INSTALLATION_GUIDE_RPI5.md - Решение проблем](INSTALLATION_GUIDE_RPI5.md#-решение-распространенных-проблем)

---

## 📊 Поддерживаемые модели

- **Triangle серия**: X2, X2L, X3, X4, **T1** ⭐
- **TOF серия**: TG15, TG30, TG50
- **TMini серия**: T-mini, T-mini Pro
- **Другие**: ETLiDAR, SCL серия

### Характеристики YDLidar T1

- Дальность: 0.12 - 16 м
- Частота: ~4 Hz
- Разрешение: 720 точек
- Baudrate: 128000
- Канал: Single (one-way)

---

## 🎓 Проверка работы

```bash
# Проверка топиков
ros2 topic list
ros2 topic hz /scan
ros2 topic echo /scan --once

# Информация о ноде
ros2 node list
ros2 node info /ydlidar_ros2_node

# Параметры
ros2 param list /ydlidar_ros2_node
```

---

## 🔄 Автозапуск (systemd)

```bash
# Создание сервиса
sudo nano /etc/systemd/system/ydlidar.service
```

```ini
[Unit]
Description=YDLidar ROS2 Node
After=network.target

[Service]
Type=simple
User=weae
Environment="PYTHONPATH=/usr/local/lib/python3/dist-packages"
WorkingDirectory=/home/weae/weae/YDLidar-SDKs
ExecStart=/home/weae/weae/YDLidar-SDKs/start_ydlidar.sh auto 2 720
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
```

```bash
# Активация
sudo systemctl daemon-reload
sudo systemctl enable ydlidar
sudo systemctl start ydlidar
```

---

## 📚 Ссылки

- [YDLidar Official Website](http://www.ydlidar.com/)
- [YDLidar SDK (Official)](https://github.com/YDLIDAR/YDLidar-SDK)
- [ROS2 Jazzy Documentation](https://docs.ros.org/en/jazzy/)
- [Этот репозиторий](https://github.com/weae-g/YDLidar-SDKs)

---

## 🤝 Вклад

Создано на основе официального YDLidar SDK с добавлением:
- Автопоиска устройств
- Оптимизации для ROS2
- Прореживания данных
- Упрощенной ноды

---

## 📄 Лицензия

См. [LICENSE.txt](LICENSE.txt)

---

## 👤 Автор

**weae-g**
- GitHub: [@weae-g](https://github.com/weae-g)
- Репозиторий: [YDLidar-SDKs](https://github.com/weae-g/YDLidar-SDKs)

---

**Версия:** 2.0 (с автопоиском и оптимизацией)  
**Дата:** 10 ноября 2025  
**Платформа:** Raspberry Pi 5, Ubuntu 24.04, ROS2 Jazzy
