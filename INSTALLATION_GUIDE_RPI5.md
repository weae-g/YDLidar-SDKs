# 📋 Полная инструкция по установке YDLidar SDK на Raspberry Pi 5
## Ubuntu 24.04 + ROS2 Jazzy

---

## Шаг 1: Установка необходимых зависимостей

```bash
# Обновление системы
sudo apt update && sudo apt upgrade -y

# Установка базовых инструментов сборки
sudo apt install -y cmake pkg-config git build-essential

# Установка Python и SWIG для Python API
sudo apt install -y python3 python3-pip swig

# Установка ROS2 зависимостей (если еще не установлены)
sudo apt install -y python3-rclpy python3-sensor-msgs python3-tf2-ros python3-geometry-msgs
```

---

## Шаг 2: Клонирование и сборка YDLidar SDK

```bash
# Переход в рабочую директорию
cd /home/weae/weae

# Использование существующего YDLidar-SDKs
cd YDLidar-SDKs

# Создание директории для сборки
mkdir -p build
cd build

# Настройка CMake
cmake ..

# Сборка SDK (использует все доступные ядра процессора)
make -j$(nproc)

# Установка SDK в систему (требует sudo)
sudo make install
```

**Ожидаемый результат:**
- Библиотека установлена в `/usr/local/lib/`
- Заголовочные файлы в `/usr/local/include/`
- Python модуль в `/usr/local/lib/python3/dist-packages/`
- Примеры в `/usr/local/bin/`

---

## Шаг 3: Настройка Python модуля YDLidar

Python модуль уже установлен командой `sudo make install` в `/usr/local/lib/python3/dist-packages/`. Нужно добавить этот путь в PYTHONPATH:

### Метод 1: Через переменную окружения (Рекомендуется)

```bash
# Добавление пути в PYTHONPATH для текущей сессии
export PYTHONPATH=/usr/local/lib/python3/dist-packages:$PYTHONPATH

# Проверка установки
python3 -c "import ydlidar; print('YDLidar SDK установлен успешно')"

# Для постоянного добавления пути, добавьте в ~/.bashrc
echo 'export PYTHONPATH=/usr/local/lib/python3/dist-packages:$PYTHONPATH' >> ~/.bashrc

# Применить изменения
source ~/.bashrc
```

### Метод 2: Создание символических ссылок

```bash
# Создаем символические ссылки в системный dist-packages
sudo ln -sf /usr/local/lib/python3/dist-packages/_ydlidar.so /usr/lib/python3/dist-packages/
sudo ln -sf /usr/local/lib/python3/dist-packages/ydlidar.py /usr/lib/python3/dist-packages/

# Проверка установки
python3 -c "import ydlidar; print('YDLidar SDK установлен успешно')"
```

**Выберите один из методов. Метод 1 безопаснее и легче откатить.**

---

## Шаг 4: Настройка прав доступа к USB устройству

```bash
# Добавление текущего пользователя в группу dialout
sudo usermod -a -G dialout $USER

# Применение изменений (перелогиньтесь или выполните)
newgrp dialout

# Проверка наличия LiDAR устройства
ls -l /dev/ttyUSB* 2>/dev/null || ls -l /dev/ttyACM* 2>/dev/null
```

### Создание udev правила (опционально, для автоматических прав)

```bash
# Создание udev правила для YDLidar
sudo bash -c 'cat > /etc/udev/rules.d/99-ydlidar.rules << EOF
# YDLidar USB devices
KERNEL=="ttyUSB*", ATTRS{idVendor}=="10c4", ATTRS{idProduct}=="ea60", MODE:="0666", GROUP:="dialout", SYMLINK+="ydlidar"
KERNEL=="ttyACM*", MODE:="0666", GROUP:="dialout"
EOF'

# Перезагрузка udev правил
sudo udevadm control --reload-rules
sudo udevadm trigger

# Переподключите LiDAR устройство
```

---

## Шаг 5: Тестирование SDK (опционально)

```bash
# Переход в директорию со сборкой
cd /home/weae/weae/YDLidar-SDKs/build

# Просмотр доступных тестовых программ
ls -1 *test* | grep -v CMake

# Запуск теста для Triangle/TOF LiDAR
./tof_test

# Или запуск универсального теста
./ydlidar_test
```

**Нажмите Ctrl+C для остановки теста.**

### Тестирование Python API

```bash
# Запуск Python примера
cd /home/weae/weae/YDLidar-SDKs
python3 -c "
import ydlidar
print('SDK версия:', ydlidar.__file__)
laser = ydlidar.CYdLidar()
print('CYdLidar создан успешно!')
"
```

---

## Шаг 6: Настройка и запуск ROS2 нод YDLidar

В репозитории доступны **две ROS2 ноды** с разными возможностями:

### 📦 Доступные ноды:

1. **`ydlidar_ros2_node.py`** - Полнофункциональная нода с оптимизацией
   - ✅ Автоматический поиск устройства
   - ✅ Прореживание данных (для предотвращения переполнения памяти)
   - ✅ Автоматический перебор baudrate
   - ✅ Все параметры настраиваемые

2. **`ydlidar_ros2_simple.py`** - Упрощенная нода
   - ✅ Автоматический поиск устройства
   - ✅ Простая инициализация без turnOn()
   - ✅ Минимальная конфигурация

### 🔧 Первоначальная настройка

```bash
# Переход к директории с нодами
cd /home/weae/weae/YDLidar-SDKs

# Проверка наличия файлов
ls -l ydlidar_ros2_node.py ydlidar_ros2_simple.py

# Сделайте скрипты исполняемыми
chmod +x ydlidar_ros2_node.py ydlidar_ros2_simple.py start_ydlidar.sh

# Убедитесь, что ROS2 окружение загружено
source /opt/ros/jazzy/setup.bash

# Добавьте PYTHONPATH (если используете Метод 1 из Шага 3)
export PYTHONPATH=/usr/local/lib/python3/dist-packages:$PYTHONPATH
```

---

## 🚀 Способы запуска

### Способ 1: Быстрый запуск через скрипт (Рекомендуется ⭐)

```bash
# Запуск с автопоиском устройства и оптимальными настройками
./start_ydlidar.sh

# С кастомными параметрами
./start_ydlidar.sh auto 2 720
#                  ↑    ↑ ↑
#                  |    | └─ Максимум точек
#                  |    └─── Прореживание (каждая 2-я точка)
#                  └──────── Порт (auto = автопоиск)

# Указать конкретный порт
./start_ydlidar.sh /dev/ttyUSB1 3 600
```

### Способ 2: Запуск основной ноды напрямую

```bash
# Запуск с автопоиском и параметрами по умолчанию
./ydlidar_ros2_node.py

# Запуск с указанием всех параметров
./ydlidar_ros2_node.py --ros-args \
  -p serial_port:=auto \
  -p baudrate:=128000 \
  -p frame_id:=laser \
  -p topic:=/scan \
  -p publish_static_tf:=true \
  -p parent_frame:=base_link \
  -p use_ros_time:=true \
  -p downsample_factor:=2 \
  -p max_points:=720
```

### Способ 3: Запуск упрощенной ноды

```bash
# Запуск с параметрами по умолчанию
./ydlidar_ros2_simple.py

# С кастомными параметрами
./ydlidar_ros2_simple.py --ros-args \
  -p serial_port:=auto \
  -p baudrate:=128000 \
  -p single_channel:=true \
  -p lidar_type:=1
```

---

## 📋 Полный список параметров

### Параметры `ydlidar_ros2_node.py`:

| Параметр | Тип | По умолчанию | Описание |
|----------|-----|--------------|----------|
| `serial_port` | string | `auto` | Порт устройства (`auto` для автопоиска, `/dev/ttyUSB0`, `/dev/ttyUSB1` и т.д.) |
| `baudrate` | int | `128000` | Скорость передачи данных (115200, 128000, 230400, 512000) |
| `frame_id` | string | `laser` | ID фрейма для LaserScan сообщений |
| `topic` | string | `/scan` | Топик для публикации данных |
| `publish_static_tf` | bool | `true` | Публиковать статический TF между parent_frame и frame_id |
| `parent_frame` | string | `base_link` | Родительский фрейм для TF |
| `use_ros_time` | bool | `true` | Использовать ROS время для штампов сообщений |
| `downsample_factor` | int | `2` | Коэффициент прореживания (1=нет, 2=каждая 2-я точка, 3=каждая 3-я и т.д.) |
| `max_points` | int | `720` | Максимальное количество точек в скане (0=без ограничений) |

### Параметры `ydlidar_ros2_simple.py`:

| Параметр | Тип | По умолчанию | Описание |
|----------|-----|--------------|----------|
| `serial_port` | string | `auto` | Порт устройства (`auto` для автопоиска) |
| `baudrate` | int | `128000` | Скорость передачи данных |
| `frame_id` | string | `laser` | ID фрейма для LaserScan |
| `topic` | string | `/scan` | Топик для публикации |
| `publish_static_tf` | bool | `true` | Публиковать статический TF |
| `parent_frame` | string | `base_link` | Родительский фрейм |
| `single_channel` | bool | `true` | Однонаправленная связь (для T1) |
| `lidar_type` | int | `1` | Тип LiDAR (1=Triangle, 2=TOF) |

---

## 💡 Примеры запуска для разных сценариев

### Для YDLidar T1 (как в вашем случае):

```bash
# Оптимальный вариант - автопоиск + прореживание
./start_ydlidar.sh auto 2 720

# Или напрямую основная нода
./ydlidar_ros2_node.py --ros-args \
  -p serial_port:=auto \
  -p downsample_factor:=2 \
  -p max_points:=720

# Или упрощенная нода
./ydlidar_ros2_simple.py --ros-args \
  -p serial_port:=auto \
  -p single_channel:=true
```

### Для слабых систем (минимальная нагрузка):

```bash
# Агрессивное прореживание
./start_ydlidar.sh auto 4 360

# Результат: ~315 точек вместо ~1260
```

### Для точных измерений (без прореживания):

```bash
# ВНИМАНИЕ: Может вызвать переполнение памяти в RViz2!
./start_ydlidar.sh auto 1 0

# Результат: все ~1260 точек
```

### С конкретным портом (если автопоиск не работает):

```bash
# Определите порт вручную
ls -l /dev/ttyUSB* /dev/ttyACM*

# Запустите с явным указанием порта
./start_ydlidar.sh /dev/ttyUSB1 2 720

# Или
./ydlidar_ros2_node.py --ros-args -p serial_port:=/dev/ttyUSB1
```

### Определение правильного порта и baudrate

```bash
# Найти подключенные устройства
ls -l /dev/ttyUSB* /dev/ttyACM* 2>/dev/null

# Проверка информации об устройстве
udevadm info -a -n /dev/ttyUSB0 | grep -i 'vendor\|product'

# Подключите LiDAR и выполните для поиска нового устройства
dmesg | tail -20

# Автоматический поиск (встроен в ноды)
# Просто используйте serial_port:=auto
```

**Распространенные значения baudrate:**
- 115200 (старые модели)
- 128000 (наиболее распространенный, T1) ⭐
- 153600
- 230400
- 512000

---

## Шаг 7: Проверка работы ROS2 ноды

Откройте **новый терминал** и выполните:

```bash
# Загрузка ROS2 окружения
source /opt/ros/jazzy/setup.bash

# Проверка списка активных топиков
ros2 topic list

# Должен быть виден топик /scan
# Вывод: /scan, /parameter_events, /rosout

# Просмотр информации о топике
ros2 topic info /scan

# Просмотр данных со сканера (нажмите Ctrl+C для остановки)
ros2 topic echo /scan

# Проверка частоты публикации
ros2 topic hz /scan

# Просмотр информации о ноде
ros2 node info /ydlidar_ros2_node
```

---

## Шаг 8: Визуализация в RViz2 (опционально)

```bash
# Запуск RViz2 (в новом терминале)
source /opt/ros/jazzy/setup.bash
rviz2
```

**Настройка RViz2:**
1. В левом нижнем углу нажмите **Add**
2. Выберите **By topic** → **/scan** → **LaserScan**
3. В левой панели **Global Options** → **Fixed Frame** → выберите `laser` или `base_link`
4. Вы должны увидеть визуализацию лазерных сканов

---

## Шаг 9: Автозапуск при загрузке (опционально)

### Создание systemd сервиса

#### Вариант 1: Использование скрипта start_ydlidar.sh (Рекомендуется)

```bash
# Создание файла сервиса
sudo nano /etc/systemd/system/ydlidar.service
```

Вставьте следующее содержимое:

```ini
[Unit]
Description=YDLidar ROS2 Node (Optimized with auto-detection)
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

#### Вариант 2: Прямой запуск ноды

```ini
[Unit]
Description=YDLidar ROS2 Node
After=network.target

[Service]
Type=simple
User=weae
Environment="PYTHONPATH=/usr/local/lib/python3/dist-packages"
WorkingDirectory=/home/weae/weae/YDLidar-SDKs
ExecStart=/bin/bash -c 'source /opt/ros/jazzy/setup.bash && /home/weae/weae/YDLidar-SDKs/ydlidar_ros2_node.py --ros-args -p serial_port:=auto -p downsample_factor:=2 -p max_points:=720'
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
```

#### Вариант 3: Упрощенная нода

```ini
[Unit]
Description=YDLidar ROS2 Simple Node
After=network.target

[Service]
Type=simple
User=weae
Environment="PYTHONPATH=/usr/local/lib/python3/dist-packages"
WorkingDirectory=/home/weae/weae/YDLidar-SDKs
ExecStart=/bin/bash -c 'source /opt/ros/jazzy/setup.bash && /home/weae/weae/YDLidar-SDKs/ydlidar_ros2_simple.py'
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
```

Сохраните (Ctrl+O, Enter, Ctrl+X).

```bash
# Перезагрузка systemd
sudo systemctl daemon-reload

# Включение автозапуска
sudo systemctl enable ydlidar.service

# Запуск сервиса
sudo systemctl start ydlidar.service

# Проверка статуса
sudo systemctl status ydlidar.service

# Просмотр логов
journalctl -u ydlidar.service -f
```

### Управление сервисом

```bash
# Остановка
sudo systemctl stop ydlidar.service

# Перезапуск
sudo systemctl restart ydlidar.service

# Отключение автозапуска
sudo systemctl disable ydlidar.service
```

---

## 🔧 Решение распространенных проблем

### Проблема: "No YDLidar device found" (при автопоиске)

```bash
# Проверьте подключение
ls -l /dev/ttyUSB* /dev/ttyACM*

# Проверьте dmesg
dmesg | grep tty

# Попробуйте указать порт вручную
./start_ydlidar.sh /dev/ttyUSB1 2 720
```

### Проблема: "Serial port does not exist"

```bash
# Проверьте подключение
ls -l /dev/ttyUSB* /dev/ttyACM*

# Переподключите LiDAR
# Затем проверьте dmesg
dmesg | tail -20
```

### Проблема: "No read/write access"

```bash
# Проверьте группы пользователя
groups

# Должна быть группа dialout
# Если нет, выполните:
sudo usermod -a -G dialout $USER
newgrp dialout
```

### Проблема: "Failed to initialize YDLidar"

**Для ydlidar_ros2_node.py:**
```bash
# Нода автоматически перебирает baudrate
# Если не помогает, попробуйте упрощенную ноду
./ydlidar_ros2_simple.py
```

**Для ydlidar_ros2_simple.py:**
```bash
# Попробуйте разные baudrate вручную
./ydlidar_ros2_simple.py --ros-args -p baudrate:=115200
./ydlidar_ros2_simple.py --ros-args -p baudrate:=230400
./ydlidar_ros2_simple.py --ros-args -p baudrate:=512000
```

### Проблема: "ModuleNotFoundError: No module named 'ydlidar'"

```bash
# Убедитесь, что PYTHONPATH установлен
echo $PYTHONPATH

# Должно содержать: /usr/local/lib/python3/dist-packages

# Если нет, добавьте:
export PYTHONPATH=/usr/local/lib/python3/dist-packages:$PYTHONPATH

# Или используйте символические ссылки (см. Шаг 3, Метод 2)
```

### Проблема: Нода запускается, но нет данных

```bash
# Проверьте, что LiDAR вращается (должен быть звук мотора)
# Проверьте правильность baudrate
# Проверьте модель LiDAR и используйте соответствующий тест

# Для отладки запустите с логами
./ydlidar_ros2_node.py --ros-args --log-level debug
```

### Проблема: RViz2 вылетает с "std::bad_alloc"

**Причина:** Слишком много точек (~1260) перегружают память

**Решение 1:** Увеличьте прореживание
```bash
# Агрессивное прореживание
./start_ydlidar.sh auto 4 360
```

**Решение 2:** Используйте упрощенную ноду без прореживания на более мощном ПК
```bash
# Только для мощных систем
./ydlidar_ros2_simple.py
```

**Решение 3:** Настройте RViz2
- Уменьшите Size (m) точек до 0.03
- Установите Decay Time = 0
- Закройте другие приложения

### Проблема: "turnOn() returned False"

**Причина:** Некоторые модели (например, T1) не поддерживают команду turnOn()

**Решение:** Используйте упрощенную ноду
```bash
./ydlidar_ros2_simple.py
```

---

## 📚 Дополнительная информация

### Сравнение нод

| Особенность | ydlidar_ros2_node.py | ydlidar_ros2_simple.py |
|-------------|---------------------|------------------------|
| Автопоиск устройства | ✅ | ✅ |
| Прореживание данных | ✅ | ❌ |
| Автоперебор baudrate | ✅ | ❌ |
| Метод инициализации | initialize() + turnOn() | только initialize() |
| Сложность настройки | Средняя (9 параметров) | Низкая (8 параметров) |
| Производительность | Оптимизированная | Базовая |
| Рекомендуется для | Production, RViz2 | Тестирование, отладка |

### Скрипты и утилиты

| Файл | Описание |
|------|----------|
| `start_ydlidar.sh` | Быстрый запуск с параметрами |
| `setup.sh` | Настройка окружения |
| `launch_ydlidar.py` | ROS2 launch файл |

### Поддерживаемые модели LiDAR

- **Triangle серия**: X2, X2L, X3, X4, **T1** ⭐
- **TOF серия**: TG15, TG30, TG50
- **TMini серия**: T-mini, T-mini Pro
- **Другие**: ETLiDAR, SCL серия

### Характеристики YDLidar T1

- **Дальность:** 0.12 - 16 м
- **Частота сканирования:** ~4 Hz
- **Разрешение:** 720 точек (фиксированное)
- **Точек на оборот:** ~1260 (до оптимизации)
- **Канал:** Single (one-way communication)
- **Baudrate:** 128000
- **USB чип:** CP2102 (VID:PID = 10c4:ea60)

### Полезные команды ROS2

```bash
# Список всех нод
ros2 node list

# Список всех топиков
ros2 topic list

# Информация о сообщении LaserScan
ros2 interface show sensor_msgs/msg/LaserScan

# Запись данных в bag файл
ros2 bag record /scan

# Воспроизведение bag файла
ros2 bag play <bag_file>
```

### Документация

- [YDLidar SDK GitHub](https://github.com/YDLIDAR/YDLidar-SDK)
- [YDLidar Official Website](http://www.ydlidar.com/)
- [ROS2 Jazzy Documentation](https://docs.ros.org/en/jazzy/)

---

## ✅ Контрольный список успешной установки

- [ ] Все зависимости установлены (Шаг 1)
- [ ] SDK собран и установлен (Шаг 2)
- [ ] Python модуль импортируется без ошибок (Шаг 3)
- [ ] Пользователь добавлен в группу dialout (Шаг 4)
- [ ] Тестовые программы запускаются (Шаг 5)
- [ ] ROS2 нода запускается без ошибок (Шаг 6)
- [ ] Топик `/scan` публикуется (Шаг 7)
- [ ] Данные видны в RViz2 (Шаг 8)

---

## 📖 Краткая справка по командам

### Запуск нод (выберите один вариант):

```bash
# Рекомендуемый способ (скрипт с автопоиском)
./start_ydlidar.sh

# Основная нода с прореживанием
./ydlidar_ros2_node.py

# Упрощенная нода без turnOn()
./ydlidar_ros2_simple.py

# С кастомными параметрами
./start_ydlidar.sh /dev/ttyUSB1 3 600
./ydlidar_ros2_node.py --ros-args -p serial_port:=auto -p downsample_factor:=2
./ydlidar_ros2_simple.py --ros-args -p serial_port:=/dev/ttyUSB1
```

### Проверка работы:

```bash
# Проверка топиков
ros2 topic list
ros2 topic hz /scan
ros2 topic echo /scan --once

# Проверка ноды
ros2 node list
ros2 node info /ydlidar_ros2_node

# Проверка параметров
ros2 param list /ydlidar_ros2_node
ros2 param get /ydlidar_ros2_node downsample_factor
```

### Отладка:

```bash
# Проверка устройства
ls -l /dev/ttyUSB* /dev/ttyACM*
dmesg | grep tty

# Проверка прав
groups
ls -l /dev/ttyUSB1

# Проверка Python модуля
echo $PYTHONPATH
python3 -c "import ydlidar; print('OK')"

# Запуск с отладочными логами
./ydlidar_ros2_node.py --ros-args --log-level debug
```

### Управление сервисом (автозапуск):

```bash
sudo systemctl start ydlidar.service
sudo systemctl stop ydlidar.service
sudo systemctl restart ydlidar.service
sudo systemctl status ydlidar.service
journalctl -u ydlidar.service -f
```

---

## 🎯 Рекомендации по использованию

### Для YDLidar T1:
```bash
# Оптимальная конфигурация
./start_ydlidar.sh auto 2 720
```

### Для слабых систем (Raspberry Pi):
```bash
# Агрессивное прореживание
./start_ydlidar.sh auto 4 360
```

### Для точных измерений:
```bash
# Без прореживания (только на мощных ПК!)
./ydlidar_ros2_simple.py
```

### При проблемах с turnOn():
```bash
# Используйте упрощенную ноду
./ydlidar_ros2_simple.py
```

---

**Версия документа:** 2.0 (с автопоиском и оптимизацией)  
**Дата обновления:** 10 ноября 2025  
**Платформа:** Raspberry Pi 5, Ubuntu 24.04, ROS2 Jazzy  
**Репозиторий:** https://github.com/weae-g/YDLidar-SDKs

---

## 📚 Дополнительные ресурсы

- [QUICK_START.md](QUICK_START.md) - Краткое руководство по запуску
- [AUTO_DETECTION.md](AUTO_DETECTION.md) - Подробно об автопоиске устройств
- [SUMMARY.md](SUMMARY.md) - Общая сводка установки
- [YDLidar SDK Documentation](https://github.com/YDLIDAR/YDLidar-SDK)
- [ROS2 Jazzy Documentation](https://docs.ros.org/en/jazzy/)
