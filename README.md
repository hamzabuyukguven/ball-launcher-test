# Ball Launcher Full System

Heybeliada top-atış simülasyonunun ROS 2, Gazebo, gRPC, Java backend/frontend,
Kafka ve bağımsız gemi kontrol paneli ile entegre edilmiş tam proje deposudur.

## Bileşenler

- ROS 2 Jazzy simülasyon paketleri
- Gazebo Harmonic deniz ortamı
- Heybeliada ve hedef gemi modelleri
- Pan/tilt rate kontrolü
- Atış komutu ve mermi oluşturma
- Simülasyon telemetrisi
- gRPC–ROS köprüsü
- Java backend
- JavaFX frontend
- Kafka ve Zookeeper
- Bağımsız Ship Control Panel
- Güncel ve eski başlatma scriptleri

## Dizin yapısı

- `ros2_ws/src/`: ROS 2 paketleri, modeller, world dosyaları ve arayüzler
- `integrated_system/`: backend, frontend, Docker ve entegrasyon scriptleri
- `ship_control_panel/`: bağımsız gemi kontrol paneli
- `phone_test/`: korunmuş eski telefon/target kontrol dosyaları
- `scripts/current/`: güncel entegre başlatma ve durdurma scriptleri
- `scripts/legacy/`: korunmuş bağımsız eski başlatma scriptleri
- `config/`: ROS–Gazebo cmd_vel bridge yapılandırmaları
- `desktop_launchers/`: Ubuntu masaüstü kısayolları
- `docs/`: manifest ve proje dokümantasyonu

## Test edilen ortam

- Ubuntu 24.04
- ROS 2 Jazzy
- Gazebo Harmonic
- Python 3.12
- Java 21
- Maven
- Docker ve Docker Compose

## Güncel entegre sistem

Başlatma:

```bash
~/start_ball_launcher_with_ship_panel.sh
```

Durdurma:

```bash
~/stop_ball_launcher_with_ship_panel.sh
```

Ship Control Panel:

```bash
~/start_ship_control_panel.sh
```

## Korunan eski sistem

Bağımsız simülasyon:

```bash
~/start_heybeliada_with_fire.sh
```

Eski telefon kontrol sistemi:

```bash
~/start_heybeliada_phone.sh
```

Bu eski dosyalar yeni panelden ayrı tutulur ve değiştirilmemelidir.

## Ana portlar

- Kafka: `9092`
- Simülasyon gRPC: `50052`
- Ship Control Panel: `8090`

## Önemli ROS topic'leri

- `/backend/gun_rate_command`
- `/backend/fire_command`
- `/backend/target_info`
- `/backend/platform_cmd_vel`
- `/test/target_cmd_vel`
- `/heybeliada/pan_cmd`
- `/heybeliada/tilt_cmd`
- `/launch_velocity`
- `/joint_states`

## Proto sözleşmesi

Backend–simülasyon gRPC sözleşmesi:

```text
ros2_ws/src/grpc_ros_bridge/proto/naval_bridge.proto
```

Backend ve simülasyon aynı proto sürümünden stub üretmelidir.

## Güvenlik

Build çıktıları, çalışma logları, PID dosyaları, gerçek `.env` dosyaları,
kimlik bilgileri ve geçici dosyalar repoya dahil edilmez.
