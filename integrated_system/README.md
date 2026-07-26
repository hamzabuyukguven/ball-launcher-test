# Ball Launcher – Entegre Çalışma Paketi

Bu paket üç uygulamayı aşağıdaki veri yolunda birleştirir:

```text
JavaFX Frontend
      │
      │ Kafka (JSON)
      ▼
Java Backend
      │
      │ gRPC / naval_bridge.proto
      ▼
ROS 2 + Gazebo Simulation
```

Phone control kaldırılmamıştır. Heybeliada ve target gemisini manuel/test amaçlı hareket ettirmek için simulation ile birlikte çalıştırılabilir.

## Klasörler

- `frontend/`: Java 21 + JavaFX + Kafka kullanıcı arayüzü
- `backend/`: Java 21 + Kafka + gRPC kontrol servisi
- `broker/`: Kafka broker için örnek ortam ayarı
- `scripts/`: ağ ve Kafka topic doğrulama araçları
- `INTEGRATION_REPORT.md`: yapılan düzeltmeler ve doğrulama durumu

## Veri akışı

### Frontend → Backend

Kafka topic: `launcher.commands`

Örnek hedef komutu:

```json
{
  "action": "SET_MANUAL_TARGET",
  "telemetry": {
    "targetX": -250.0,
    "targetY": 220.0,
    "targetZ": 0.0
  }
}
```

Örnek atış isteği:

```json
{
  "action": "FIRE",
  "telemetry": {
    "targetX": -250.0,
    "targetY": 220.0,
    "targetZ": 0.0
  }
}
```

Backend `FIRE` geldiği anda doğrudan ateş etmez. Hedefe hizalanmayı, simulation/gun hazır bilgisini, arıza olmamasını ve mühimmat bulunmasını bekler. Koşullar sağlanınca `SendFireCommand` RPC’sini bir kez gönderir.

Desteklenen aksiyonlar:

- `SET_MANUAL_TARGET`
- `USE_TRACKED_TARGET`
- `FIRE`
- `STOW`
- `EMERGENCY_STOP`
- `CLEAR_EMERGENCY_STOP`

### Backend → Frontend

- `launcher.status`: bağlantı, hazır olma ve sistem durumu
- `launcher.telemetry`: platform konumu, pan/tilt, mühimmat ve hizalama
- `launcher.reports`: fault/hata raporları

### Backend ↔ Simulation

Backend, `backend/src/main/proto/naval_bridge.proto` sözleşmesini kullanır.

Komut RPC’leri:

- `SendGunRateCommand`
- `SendFireCommand`

Okunan stream’ler:

- `StreamGunInfo`
- `StreamGunStatus`
- `StreamPlatformPosition`
- `StreamTargetPosition`
- `StreamStabilizationData`
- `StreamPlatformStatus`
- `StreamHeartbeat`

Kesilen stream’ler iki saniye sonra otomatik yeniden açılır.

## Gereksinimler

Her Java bilgisayarında:

```bash
java -version
mvn -version
```

Beklenen Java sürümü: **21**.

Kafka için Docker kullanılıyorsa:

```bash
docker --version
docker compose version
```

## 1. Kafka broker’ı başlat

Kafka’nın çalışacağı bilgisayarın yerel ağ IP’sini belirle:

```bash
hostname -I
```

Örnek IP `192.168.1.50` ise:

```bash
cd backend
export KAFKA_ADVERTISED_HOST=192.168.1.50
docker compose up -d
```

Topicleri oluştur:

```bash
../scripts/create-kafka-topics.sh
```

Broker ve istemciler aynı bilgisayardaysa `KAFKA_ADVERTISED_HOST=127.0.0.1` kullanılabilir. Ayrı bilgisayarlardaysa kesinlikle broker bilgisayarının diğer makinelerden erişilebilir LAN IP’sini kullan.

## 2. Simulation’ı başlat

Simulation bilgisayarında mevcut sistem korunur:

```bash
~/start_heybeliada_sydney.sh
```

Kullandığın güncel başlangıç scripti farklıysa onu çalıştır. Ardından aşağıdakileri doğrula:

```bash
ros2 node list | grep -E 'naval_bridge_server|simulation_telemetry_node|gun_rate_controller|fire_command_adapter|ball_spawner'

ss -ltnp | grep 50052
```

Beklenen gRPC portu: `50052`.

## 3. Backend’i başlat

Backend bilgisayarında:

```bash
cd backend
export KAFKA_BOOTSTRAP_SERVERS=<KAFKA_BROKER_IP>:9092
export SIMULATION_GRPC_HOST=<SIMULATION_PC_IP>
export SIMULATION_GRPC_PORT=50052
export CONTROL_ENABLED=true
./run-backend.sh
```

Örnek:

```bash
export KAFKA_BOOTSTRAP_SERVERS=192.168.1.50:9092
export SIMULATION_GRPC_HOST=192.168.1.60
export SIMULATION_GRPC_PORT=50052
export CONTROL_ENABLED=true
./run-backend.sh
```

## 4. Frontend’i başlat

Frontend bilgisayarında:

```bash
cd frontend
export KAFKA_BOOTSTRAP_SERVERS=<KAFKA_BROKER_IP>:9092
./run-frontend.sh
```

## Phone control ile birlikte kullanım

### Önerilen normal kullanım

- Phone control: Heybeliada ve target gemisinin hareketi
- Frontend + backend: hedef/top/atış yönetimi
- Hareketli target gemisini otomatik izlemek için frontend’de **SIMULATION TARGET STREAM'İNİ KULLAN**
- `CONTROL_ENABLED=true`

Bu senaryoda phone control’ün platform ve target hareket topicleri kullanılabilir. Aynı anda phone control’den top rate/fire komutu gönderme.

### Phone control ile topu da manuel yönetme

Backend’in topa komut göndermesini kapat:

```bash
export CONTROL_ENABLED=false
./run-backend.sh
```

Bu modda backend Kafka ve gRPC telemetrisini frontend’e taşımaya devam eder ancak pan/tilt/fire komutu üretmez. Frontend durum alanında `MANUAL_CONTROL` görünür.

## Ağ kontrolü

Frontend/backend bilgisayarından:

```bash
./scripts/check-connections.sh <KAFKA_BROKER_IP> <SIMULATION_PC_IP>
```

Örnek:

```bash
./scripts/check-connections.sh 192.168.1.50 192.168.1.60
```

## Yapılandırma

Bütün sabit IP ve portlar ortam değişkeniyle ezilebilir.

Backend için önemli değişkenler:

```text
KAFKA_BOOTSTRAP_SERVERS
SIMULATION_GRPC_HOST
SIMULATION_GRPC_PORT
CONTROL_ENABLED
CONTROL_RATE_HZ
MUZZLE_VELOCITY
FIRE_RETRY_INTERVAL_MS
MAX_PAN_RATE
MAX_TILT_RATE
AIM_TOLERANCE_DEG
AMMO_INITIAL_COUNT
AMMO_TYPE
```

Frontend için:

```text
KAFKA_BOOTSTRAP_SERVERS
KAFKA_COMMAND_TOPIC
KAFKA_STATUS_TOPIC
KAFKA_TELEMETRY_TOPIC
KAFKA_REPORTS_TOPIC
```

Varsayılanlar ilgili `config.properties` dosyalarındadır.

## Uçtan uca test sırası

1. Kafka broker açık mı?
2. Simulation gRPC portu `50052` dinliyor mu?
3. Backend logunda Kafka ve simulation adresleri doğru mu?
4. Frontend `BAĞLI` durumuna geçiyor mu?
5. Phone control ile target gemisini hareket ettirince simulation hedef stream’i güncelleniyor mu?
6. Frontend’den hedef gönderilince top hedefe yöneliyor mu?
7. Pan/tilt durduğunda `HİZALI` ve `ATEŞE HAZIR` görünüyor mu?
8. Atış isteği yalnızca hazır koşullarında bir kez gerçekleşiyor mu?
9. Mühimmat sayısı bir azalıyor mu?
10. Simulation kapatılınca frontend bağlantı durumu düşüyor, yeniden açılınca stream’ler toparlanıyor mu?
