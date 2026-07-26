#!/usr/bin/env python3

import json
import math
import shlex
import subprocess
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

HOST = "0.0.0.0"
PORT = 8080

# ROS 2 projenin bulunduğu workspace
ROS_SETUP = (
    "source /opt/ros/jazzy/setup.bash && "
    "source ~/naval_launcher_ws/install/setup.bash"
)

pan_degree = 0.0
tilt_degree = 0.0
state_lock = threading.Lock()


HTML_PAGE = r"""
<!DOCTYPE html>
<html lang="tr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport"
          content="width=device-width, initial-scale=1.0, maximum-scale=1.0">

    <title>Top Atışı Kontrol Paneli</title>

    <style>
        body {
            font-family: Arial, sans-serif;
            background: #101820;
            color: white;
            margin: 0;
            padding: 18px;
        }

        .container {
            max-width: 520px;
            margin: auto;
        }

        .card {
            background: #1d2a35;
            border-radius: 14px;
            padding: 18px;
            margin-bottom: 16px;
        }

        h1 {
            font-size: 25px;
            text-align: center;
        }

        h2 {
            font-size: 19px;
            margin-top: 0;
        }

        label {
            display: block;
            margin-top: 12px;
            margin-bottom: 5px;
        }

        input {
            box-sizing: border-box;
            width: 100%;
            padding: 12px;
            font-size: 18px;
            border-radius: 8px;
            border: 1px solid #607080;
        }

        button {
            border: none;
            border-radius: 10px;
            padding: 14px;
            font-size: 18px;
            font-weight: bold;
            cursor: pointer;
        }

        .fire {
            width: 100%;
            margin-top: 18px;
            background: #d93636;
            color: white;
        }

        .move {
            background: #3178c6;
            color: white;
            min-width: 82px;
        }

        .stop {
            background: #e0a800;
            color: black;
        }

        .movement {
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 9px;
            text-align: center;
        }

        .empty {
            visibility: hidden;
        }

        #status {
            margin-top: 15px;
            padding: 12px;
            background: #0c141a;
            border-radius: 8px;
            min-height: 24px;
            white-space: pre-wrap;
        }

        .small {
            color: #b9c5cf;
            font-size: 14px;
        }
    </style>
</head>

<body>
<div class="container">

    <h1>Heybeliada Top Kontrolü</h1>

    <div class="card">
        <h2>Manuel Top Hareketi</h2>

        <div class="movement">
            <button class="empty">-</button>
            <button class="move" onclick="moveGun('up')">Yukarı</button>
            <button class="empty">-</button>

            <button class="move" onclick="moveGun('left')">Sol</button>
            <button class="stop" onclick="moveGun('center')">Merkez</button>
            <button class="move" onclick="moveGun('right')">Sağ</button>

            <button class="empty">-</button>
            <button class="move" onclick="moveGun('down')">Aşağı</button>
            <button class="empty">-</button>
        </div>

        <p class="small">
            Sağ-sol hareket 5 derece, yukarı-aşağı hareket 3 derece değişir.
        </p>
    </div>

    <div class="card">
        <h2>Hedef ve Ateşleme</h2>

        <label for="x">Hedef X koordinatı</label>
        <input id="x" type="number" step="0.1" value="20">

        <label for="y">Hedef Y koordinatı</label>
        <input id="y" type="number" step="0.1" value="0">

        <label for="leftRpm">Sol motor RPM</label>
        <input id="leftRpm" type="number" step="1" value="5000">

        <label for="rightRpm">Sağ motor RPM</label>
        <input id="rightRpm" type="number" step="1" value="5000">

        <button class="fire" onclick="fireGun()">ATEŞ ET</button>

        <div id="status">Sunucu bağlantısı hazır.</div>
    </div>

</div>

<script>
    const statusBox = document.getElementById("status");

    async function sendRequest(path, payload) {
        statusBox.textContent = "Komut gönderiliyor...";

        try {
            const response = await fetch(path, {
                method: "POST",
                headers: {
                    "Content-Type": "application/json"
                },
                body: JSON.stringify(payload)
            });

            const result = await response.json();

            if (!response.ok) {
                throw new Error(result.message || "Komut başarısız");
            }

            statusBox.textContent = result.message;
        } catch (error) {
            statusBox.textContent = "HATA: " + error.message;
        }
    }

    function moveGun(direction) {
        sendRequest("/move", {
            direction: direction
        });
    }

    function fireGun() {
        sendRequest("/fire", {
            x: Number(document.getElementById("x").value),
            y: Number(document.getElementById("y").value),
            left_rpm: Number(document.getElementById("leftRpm").value),
            right_rpm: Number(document.getElementById("rightRpm").value)
        });
    }
</script>
</body>
</html>
"""


def run_ros_command(arguments):
    """ROS 2 komutunu workspace ortamı kaynaklandıktan sonra çalıştırır."""

    ros_command = shlex.join(arguments)
    complete_command = f"{ROS_SETUP} && {ros_command}"

    result = subprocess.run(
        ["bash", "-lc", complete_command],
        capture_output=True,
        text=True,
        timeout=15
    )

    if result.returncode != 0:
        error_message = result.stderr.strip() or result.stdout.strip()
        raise RuntimeError(error_message or "ROS 2 komutu başarısız oldu.")

    return result.stdout.strip()


def publish_float64(topic, value):
    message = f"{{data: {value:.8f}}}"

    return run_ros_command([
        "ros2",
        "topic",
        "pub",
        "--once",
        topic,
        "std_msgs/msg/Float64",
        message
    ])


def publish_fire_request():
    """Topun ateşlenmesi için fire_request topic'ine true gönderir."""

    return run_ros_command([
        "ros2",
        "topic",
        "pub",
        "--once",
        "/simulation/fire_request",
        "std_msgs/msg/Bool",
        "{data: true}"
    ])


class PhoneControlHandler(BaseHTTPRequestHandler):

    def send_json(self, status_code, payload):
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")

        self.send_response(status_code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path != "/":
            self.send_error(404)
            return

        page = HTML_PAGE.encode("utf-8")

        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(page)))
        self.end_headers()
        self.wfile.write(page)

    def do_POST(self):
        try:
            content_length = int(self.headers.get("Content-Length", "0"))
            raw_body = self.rfile.read(content_length)
            data = json.loads(raw_body.decode("utf-8"))

            if self.path == "/fire":
                self.handle_fire(data)
                return

            if self.path == "/move":
                self.handle_move(data)
                return

            self.send_json(404, {
                "message": "Bilinmeyen komut."
            })

        except subprocess.TimeoutExpired:
            self.send_json(504, {
                "message": "ROS 2 komutu zaman aşımına uğradı."
            })

        except Exception as error:
            self.send_json(500, {
                "message": str(error)
            })

    def handle_fire(self, data):
        publish_fire_request()

        self.send_json(200, {
            "message": "Fire command sent successfully."
        })

    def handle_move(self, data):
        global pan_degree, tilt_degree

        direction = str(data.get("direction", "")).lower()

        with state_lock:
            if direction == "left":
                pan_degree -= 5.0

            elif direction == "right":
                pan_degree += 5.0

            elif direction == "up":
                tilt_degree += 3.0

            elif direction == "down":
                tilt_degree -= 3.0

            elif direction == "center":
                pan_degree = 0.0
                tilt_degree = 0.0

            else:
                raise ValueError("Geçersiz hareket komutu.")

            # Güvenli manuel hareket sınırları
            pan_degree = max(-90.0, min(90.0, pan_degree))
            tilt_degree = max(0.0, min(45.0, tilt_degree))

            pan_radian = math.radians(pan_degree)
            tilt_radian = math.radians(tilt_degree)

        publish_float64("/heybeliada/pan_cmd", pan_radian)
        publish_float64("/heybeliada/tilt_cmd", tilt_radian)

        self.send_json(200, {
            "message": (
                "Top hareket komutu gönderildi.\n"
                f"Pan: {pan_degree:.1f} derece\n"
                f"Tilt: {tilt_degree:.1f} derece"
            )
        })

    def log_message(self, format_string, *args):
        print(
            f"{self.client_address[0]} - "
            f"{format_string % args}"
        )


if __name__ == "__main__":
    server = ThreadingHTTPServer(
        (HOST, PORT),
        PhoneControlHandler
    )

    print("=" * 55)
    print("Phone control server is running")
    print(f"Address: http://0.0.0.0:{PORT}")
    print("Press Ctrl+C to stop")
    print("=" * 55)

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nSunucu kapatılıyor...")
    finally:
        server.server_close()
