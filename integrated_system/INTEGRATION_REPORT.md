# Entegrasyon ve Düzeltme Raporu

## Korunan davranış

- Phone control dosyaları değiştirilmedi ve entegrasyon paketine bağımlı hale getirilmedi.
- Phone control, Heybeliada/target hareketi için ayrı manuel-test katmanı olarak kullanılabilir.
- Backend top kontrolünü kapatmak için `CONTROL_ENABLED=false` modu eklendi.

## Düzeltilen frontend sorunları

1. Frontend’in hedef telemetrisini `launcher.telemetry` topic’ine yazması kaldırıldı.
   - Hedef artık `launcher.commands` içindeki `SET_MANUAL_TARGET` komutuyla gönderiliyor.
   - Backend durum telemetrisiyle frontend hedef mesajlarının aynı topic içinde karışması engellendi.
2. Frontend hem `launcher.status` hem `launcher.telemetry` topic’ini dinliyor.
3. `SystemStatus` modeline `aimed` ve `readyToFire` alanları eklendi.
4. Jackson bilinmeyen ek alanları reddetmeyecek şekilde ayarlandı.
5. Arayüzün kendi kendine üç saniye sonra `READY` olması kaldırıldı.
6. Hazır/hizalı/bağlantı bilgileri yalnızca backend’den gelen gerçek veriye bağlandı.
7. FXML anchor/yapı hataları temizlendi ve bütün `fx:id` / action eşleşmeleri yeniden kuruldu.
8. Kafka broker, topic ve consumer group ayarları ortam değişkeniyle yapılandırılabilir hale getirildi.
9. Producer idempotent ve `acks=all` çalışacak şekilde ayarlandı.
10. Consumer kapanışı `wakeup()` ile güvenli hale getirildi.

## Düzeltilen backend sorunları

1. Hatalı biçimde yazılmış `config.properties` gerçek Java properties biçimine çevrildi.
2. Sabit Kafka ve gRPC IP’leri kaldırıldı.
3. Java sürümü frontend ile aynı olacak şekilde Java 21’e getirildi.
4. Frontend komut modeliyle Kafka JSON sözleşmesi eşleştirildi.
5. Pan/tilt komutu tek seferlik olmaktan çıkarılıp yapılandırılabilir 20 Hz kapalı çevrim kontrol döngüsüne taşındı.
6. Dünya hedef koordinatı, ownship konumu ve yaw bilgisine göre göreli pan/tilt hedefi hesaplanıyor.
7. `FIRE` anlık ateş yerine güvenli pending-fire kuyruğuna dönüştürüldü.
8. Atış öncesi simulation ready, gun ready, hizalama, fault ve mühimmat kontrolleri eklendi.
9. Başarılı atıştan sonra mühimmat sayacı azaltılıyor.
10. Reddedilen atış RPC’sinin 20 Hz spam üretmemesi için yeniden deneme aralığı eklendi.
11. Gerçek gRPC channel durumu Kafka status olarak yayımlanıyor; transport bağlantısı simulation-ready bilgisinin yerine kullanılmıyor.
12. Kopan gRPC stream’leri otomatik yeniden bağlanıyor.
13. Manuel koordinat ile hareketli simulation target stream’i arasında açık hedef-kaynağı seçimi eklendi.
14. STOW sonrası target stream’in topu kendiliğinden tekrar devralması engellendi.
15. Eski/kullanılmayan ikinci `launcher.proto` ve yorum satırındaki TCP taslakları temizlendi.
16. Docker Compose Kafka advertised host sabit IP olmaktan çıkarıldı.

## Kafka topic sözleşmesi

| Topic | Yön | İçerik |
|---|---|---|
| `launcher.commands` | Frontend → Backend | `LaunchCommand` |
| `launcher.status` | Backend → Frontend | bağlantı/hazır durumu |
| `launcher.telemetry` | Backend → Frontend | konum, açı, mühimmat, hizalama |
| `launcher.reports` | Backend → Frontend | fault ve hata raporları |

## Doğrulama kapsamı

Yapılan yerel kontroller:

- ZIP açılımı ve kaynak ağacı incelemesi
- Frontend/backend topic adı karşılaştırması
- Kafka JSON model alanlarının karşılaştırılması
- Hard-coded IP taraması
- Eski constructor ve legacy proto referans taraması
- POM/FXML XML ayrıştırma kontrolü
- Java kaynak yapısı ve paket-yol kontrolü
- Tüm backend ve frontend Java kaynaklarının dış API stub’larıyla tam derleme kontrolü
- `naval_bridge.proto` protobuf sözdizimi ve Java/gRPC çıktı üretme kontrolü
- Bash script sözdizimi kontrolü
- Kapalı çevrim davranış testi: hizalanmadan ateş yok, hizalanınca tek atış, mühimmat sayacı bir azalıyor

Bu çalışma ortamında Maven, Kafka broker, ROS 2 ve Gazebo servisleri bulunmadığı için gerçek ağ üzerinde `mvn package` ve canlı uçtan uca atış testi çalıştırılamadı. Paket, proje bilgisayarlarında README’deki sırayla derlenip gerçek simulation üzerinde doğrulanmalıdır.
