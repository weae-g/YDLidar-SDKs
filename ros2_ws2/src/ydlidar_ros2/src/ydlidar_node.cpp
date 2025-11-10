#include "rclcpp/rclcpp.hpp"
#include "sensor_msgs/msg/laser_scan.hpp"
#include "CYdLidar.h"
#include <limits>

using namespace std;
using namespace ydlidar;

class YDLidarNode : public rclcpp::Node
{
public:
    YDLidarNode()
    : Node("ydlidar_node")
    {
        // Паблишер сканов
        publisher_ = this->create_publisher<sensor_msgs::msg::LaserScan>("/scan", 5);

        // Инициализация SDK
        os_init();
        laser_ = new CYdLidar();

        // Настройки LiDAR
        string port = "/dev/ttyUSB0";
        int baudrate = 128000;
        bool single_channel = true;    // T1 одноканальный
        float frequency = 7.0f;        // безопасная частота сканирования

        laser_->setlidaropt(LidarPropSerialPort, port.c_str(), port.size());
        laser_->setlidaropt(LidarPropSerialBaudrate, &baudrate, sizeof(int));

        int sample_rate = single_channel ? 3 : 4;
        int lidar_type = TYPE_TRIANGLE;
        int device_type = YDLIDAR_TYPE_SERIAL;

        laser_->setlidaropt(LidarPropSampleRate, &sample_rate, sizeof(int));
        laser_->setlidaropt(LidarPropLidarType, &lidar_type, sizeof(int));
        laser_->setlidaropt(LidarPropDeviceType, &device_type, sizeof(int));
        laser_->setlidaropt(LidarPropSingleChannel, &single_channel, sizeof(bool));
        laser_->setlidaropt(LidarPropScanFrequency, &frequency, sizeof(float));

        // Инициализация и включение LiDAR
        if (!laser_->initialize()) {
            RCLCPP_ERROR(this->get_logger(), "Failed to initialize LiDAR");
            return;
        }

        if (!laser_->turnOn()) {
            RCLCPP_ERROR(this->get_logger(), "Failed to turn on LiDAR");
            return;
        }

        RCLCPP_INFO(this->get_logger(), "LiDAR is running!");

        // Таймер публикации каждые 200 мс (~5 Hz)
        timer_ = this->create_wall_timer(
            std::chrono::milliseconds(200),
            std::bind(&YDLidarNode::publish_scan, this)
        );
    }

    ~YDLidarNode()
    {
        laser_->turnOff();
        laser_->disconnecting();
        os_shutdown();
        delete laser_;
    }

private:
    void publish_scan()
    {
        LaserScan scan;
        if (!laser_->doProcessSimple(scan)) {
            RCLCPP_WARN(this->get_logger(), "Failed to get LiDAR data");
            return;
        }

        auto msg = sensor_msgs::msg::LaserScan();
        msg.header.stamp = this->get_clock()->now();
        msg.header.frame_id = "laser";

        auto cfg = scan.config;
        msg.angle_min = cfg.min_angle;
        msg.angle_max = cfg.max_angle;
        msg.angle_increment = cfg.angle_increment;
        msg.time_increment = cfg.time_increment;
        msg.scan_time = cfg.scan_time;
        msg.range_min = cfg.min_range;
        msg.range_max = cfg.max_range;

        size_t npoints = scan.points.size();
        size_t step = 2; // публикуем каждую вторую точку, чтобы снизить нагрузку
        size_t out_points = (npoints + step - 1) / step;

        msg.ranges.resize(out_points);
        msg.intensities.resize(out_points);

        for (size_t i = 0, j = 0; i < npoints; i += step, ++j) {
            auto p = scan.points[i];
            float range = p.range;

            // Фильтр некорректных данных
            if (range < cfg.min_range || range > cfg.max_range) {
                range = std::numeric_limits<float>::infinity();
            }

            msg.ranges[j] = range;
            msg.intensities[j] = p.intensity;
        }

        publisher_->publish(msg);
    }

    rclcpp::Publisher<sensor_msgs::msg::LaserScan>::SharedPtr publisher_;
    rclcpp::TimerBase::SharedPtr timer_;
    CYdLidar* laser_;
};

int main(int argc, char **argv)
{
    rclcpp::init(argc, argv);
    auto node = std::make_shared<YDLidarNode>();
    rclcpp::spin(node);
    rclcpp::shutdown();
    return 0;
}
