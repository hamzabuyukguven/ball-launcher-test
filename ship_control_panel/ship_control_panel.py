#!/usr/bin/env python3
import json
import math
import os
import signal
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Dict

import rclpy
from geometry_msgs.msg import Twist
from rclpy.node import Node


HOST = os.environ.get("SHIP_PANEL_HOST", "0.0.0.0")
PORT = int(os.environ.get("SHIP_PANEL_PORT", "8090"))

SHIP_FORWARD_SIGN = float(os.environ.get("SHIP_FORWARD_SIGN", "1.0"))
SHIP_YAW_SIGN = float(os.environ.get("SHIP_YAW_SIGN", "1.0"))
TARGET_FORWARD_SIGN = float(os.environ.get("TARGET_FORWARD_SIGN", "1.0"))
TARGET_YAW_SIGN = float(os.environ.get("TARGET_YAW_SIGN", "1.0"))

MAX_FORWARD_SPEED = float(os.environ.get("SHIP_PANEL_MAX_FORWARD_SPEED", "2.0"))
MAX_YAW_RATE = float(os.environ.get("SHIP_PANEL_MAX_YAW_RATE", "0.20"))
COMMAND_TIMEOUT = float(os.environ.get("SHIP_PANEL_COMMAND_TIMEOUT", "0.40"))
PUBLISH_PERIOD = 0.05


PAGE = r"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1,user-scalable=no">
  <title>Ship Control Panel</title>
  <style>
    :root {
      color-scheme: dark;
      font-family: system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    }

    * { box-sizing: border-box; }

    body {
      margin: 0;
      background: #10151c;
      color: #f5f7fa;
      overscroll-behavior: none;
      touch-action: manipulation;
    }

    main {
      max-width: 980px;
      margin: 0 auto;
      padding: 18px;
    }

    h1 {
      margin: 0 0 6px;
      font-size: 1.55rem;
    }

    .subtitle {
      color: #aeb8c5;
      margin-bottom: 16px;
    }

    .controls {
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 16px;
    }

    .card {
      background: #19222d;
      border: 1px solid #2c3948;
      border-radius: 18px;
      padding: 16px;
    }

    h2 {
      margin: 0 0 5px;
      font-size: 1.2rem;
    }

    .topic {
      color: #91a0b2;
      font-size: 0.82rem;
      margin-bottom: 14px;
      word-break: break-all;
    }

    .joystick-wrap {
      display: flex;
      justify-content: center;
      padding: 4px 0 8px;
    }

    .joystick {
      position: relative;
      width: min(72vw, 290px);
      aspect-ratio: 1;
      border-radius: 50%;
      border: 2px solid #526276;
      background:
        linear-gradient(#2c3948 0 0) center / 2px 84% no-repeat,
        linear-gradient(90deg, #2c3948 0 0) center / 84% 2px no-repeat,
        radial-gradient(circle, #202b38 0 29%, #1b2530 30% 63%, #17202a 64%);
      touch-action: none;
      user-select: none;
    }

    .joystick::before,
    .joystick::after {
      position: absolute;
      color: #8f9dad;
      font-size: 0.78rem;
      pointer-events: none;
    }

    .joystick::before {
      content: "FORWARD";
      top: 9px;
      left: 50%;
      transform: translateX(-50%);
    }

    .joystick::after {
      content: "REVERSE";
      bottom: 9px;
      left: 50%;
      transform: translateX(-50%);
    }

    .left-label,
    .right-label {
      position: absolute;
      top: 50%;
      color: #8f9dad;
      font-size: 0.78rem;
      pointer-events: none;
      transform: translateY(-50%);
    }

    .left-label { left: 8px; }
    .right-label { right: 8px; }

    .knob {
      position: absolute;
      left: 50%;
      top: 50%;
      width: 31%;
      aspect-ratio: 1;
      border-radius: 50%;
      transform: translate(-50%, -50%);
      background: #47719b;
      border: 2px solid #80a7ca;
      box-shadow: 0 8px 20px rgb(0 0 0 / 35%);
      pointer-events: none;
    }

    .joystick.active .knob {
      background: #5687b4;
    }

    .readout {
      margin-top: 10px;
      display: grid;
      grid-template-columns: repeat(2, 1fr);
      gap: 8px;
      font-variant-numeric: tabular-nums;
    }

    .readout div {
      background: #131b24;
      border: 1px solid #2c3948;
      border-radius: 10px;
      padding: 9px;
      text-align: center;
    }

    .readout span {
      display: block;
      color: #91a0b2;
      font-size: 0.78rem;
      margin-bottom: 2px;
    }

    .settings {
      margin-top: 16px;
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 16px;
    }

    label {
      display: block;
    }

    input[type=range] {
      width: 100%;
      margin-top: 10px;
    }

    .value {
      color: #8fc7ff;
      font-variant-numeric: tabular-nums;
    }

    button {
      min-height: 54px;
      border: 1px solid #5f7185;
      border-radius: 13px;
      background: #263445;
      color: #fff;
      font-size: 1rem;
      font-weight: 650;
    }

    .all-stop {
      width: 100%;
      margin-top: 16px;
      background: #8c2f38;
      border-color: #bd5961;
    }

    #status {
      margin-top: 12px;
      min-height: 24px;
      color: #aeb8c5;
    }

    .note {
      margin-top: 12px;
      color: #91a0b2;
      font-size: 0.9rem;
    }

    @media (max-width: 700px) {
      .controls,
      .settings {
        grid-template-columns: 1fr;
      }

      main { padding: 12px; }

      .joystick {
        width: min(78vw, 310px);
      }
    }
  </style>
</head>
<body>
<main>
  <h1>Ship Control Panel</h1>
  <div class="subtitle">
    Independent ship movement only. This panel never publishes gun, fire, or auto-aim commands.
  </div>

  <section class="controls">
    <article class="card">
      <h2>Heybeliada</h2>
      <div class="topic">/backend/platform_cmd_vel</div>
      <div class="joystick-wrap">
        <div class="joystick" data-vessel="ship" aria-label="Heybeliada joystick">
          <div class="left-label">LEFT</div>
          <div class="right-label">RIGHT</div>
          <div class="knob"></div>
        </div>
      </div>
      <div class="readout">
        <div><span>Forward speed</span><strong data-forward="ship">0.00 m/s</strong></div>
        <div><span>Yaw rate</span><strong data-yaw="ship">0.00 rad/s</strong></div>
      </div>
    </article>

    <article class="card">
      <h2>Target Ship</h2>
      <div class="topic">/test/target_cmd_vel</div>
      <div class="joystick-wrap">
        <div class="joystick" data-vessel="target" aria-label="Target ship joystick">
          <div class="left-label">LEFT</div>
          <div class="right-label">RIGHT</div>
          <div class="knob"></div>
        </div>
      </div>
      <div class="readout">
        <div><span>Forward speed</span><strong data-forward="target">0.00 m/s</strong></div>
        <div><span>Yaw rate</span><strong data-yaw="target">0.00 rad/s</strong></div>
      </div>
    </article>
  </section>

  <section class="settings">
    <div class="card">
      <label>
        Maximum forward speed:
        <span class="value" id="speedValue">1.00 m/s</span>
        <input id="speed" type="range" min="0.20" max="2.00" step="0.05" value="1.00">
      </label>
    </div>

    <div class="card">
      <label>
        Maximum turn rate:
        <span class="value" id="turnValue">0.10 rad/s</span>
        <input id="turn" type="range" min="0.02" max="0.20" step="0.01" value="0.10">
      </label>
    </div>
  </section>

  <button class="all-stop" id="allStop" type="button">STOP BOTH SHIPS</button>
  <div id="status" aria-live="polite">Panel ready.</div>
  <div class="note">Release a joystick to stop that ship. A watchdog also stops stale commands automatically.</div>
</main>

<script>
  const speedSlider = document.getElementById("speed");
  const turnSlider = document.getElementById("turn");
  const speedValue = document.getElementById("speedValue");
  const turnValue = document.getElementById("turnValue");
  const status = document.getElementById("status");

  const states = new Map();

  function updateSliderLabels() {
    speedValue.textContent = Number(speedSlider.value).toFixed(2) + " m/s";
    turnValue.textContent = Number(turnSlider.value).toFixed(2) + " rad/s";
  }

  async function send(vessel, forward, yaw) {
    try {
      const response = await fetch("/command", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({vessel, forward, yaw}),
        keepalive: true
      });

      if (!response.ok) {
        throw new Error("HTTP " + response.status);
      }
    } catch (error) {
      status.textContent = "Command failed: " + error.message;
    }
  }

  function setReadout(vessel, forward, yaw) {
    document.querySelector(`[data-forward="${vessel}"]`).textContent =
      forward.toFixed(2) + " m/s";
    document.querySelector(`[data-yaw="${vessel}"]`).textContent =
      yaw.toFixed(2) + " rad/s";
  }

  function stopJoystick(element, sendStop = true) {
    const vessel = element.dataset.vessel;
    const state = states.get(vessel);

    if (!state) return;

    if (state.timer !== null) {
      clearInterval(state.timer);
      state.timer = null;
    }

    state.active = false;
    state.forward = 0;
    state.yaw = 0;
    element.classList.remove("active");

    const knob = element.querySelector(".knob");
    knob.style.transform = "translate(-50%, -50%)";

    setReadout(vessel, 0, 0);

    if (sendStop) {
      send(vessel, 0, 0);
      status.textContent = vessel === "ship"
        ? "Heybeliada stopped."
        : "Target ship stopped.";
    }
  }

  function updateJoystick(element, clientX, clientY) {
    const vessel = element.dataset.vessel;
    const state = states.get(vessel);
    const rect = element.getBoundingClientRect();

    const centerX = rect.left + rect.width / 2;
    const centerY = rect.top + rect.height / 2;
    const maxRadius = rect.width * 0.35;

    let dx = clientX - centerX;
    let dy = clientY - centerY;
    const magnitude = Math.hypot(dx, dy);

    if (magnitude > maxRadius) {
      const scale = maxRadius / magnitude;
      dx *= scale;
      dy *= scale;
    }

    let normalizedX = dx / maxRadius;
    let normalizedY = dy / maxRadius;

    const deadZone = 0.08;
    if (Math.abs(normalizedX) < deadZone) normalizedX = 0;
    if (Math.abs(normalizedY) < deadZone) normalizedY = 0;

    const maxSpeed = Number(speedSlider.value);
    const maxTurn = Number(turnSlider.value);

    // Screen up is negative Y, therefore it becomes positive forward speed.
    state.forward = -normalizedY * maxSpeed;

    // Joystick right means a right turn, which is negative ROS yaw.
    state.yaw = -normalizedX * maxTurn;

    const knob = element.querySelector(".knob");
    knob.style.transform =
      `translate(calc(-50% + ${dx}px), calc(-50% + ${dy}px))`;

    setReadout(vessel, state.forward, state.yaw);
  }

  document.querySelectorAll(".joystick").forEach((element) => {
    const vessel = element.dataset.vessel;

    states.set(vessel, {
      active: false,
      pointerId: null,
      timer: null,
      forward: 0,
      yaw: 0
    });

    element.addEventListener("pointerdown", (event) => {
      event.preventDefault();

      const state = states.get(vessel);
      state.active = true;
      state.pointerId = event.pointerId;
      element.setPointerCapture(event.pointerId);
      element.classList.add("active");

      updateJoystick(element, event.clientX, event.clientY);
      send(vessel, state.forward, state.yaw);

      if (state.timer !== null) clearInterval(state.timer);
      state.timer = setInterval(() => {
        if (state.active) {
          send(vessel, state.forward, state.yaw);
        }
      }, 100);

      status.textContent = vessel === "ship"
        ? "Controlling Heybeliada."
        : "Controlling target ship.";
    });

    element.addEventListener("pointermove", (event) => {
      const state = states.get(vessel);
      if (!state.active || state.pointerId !== event.pointerId) return;
      event.preventDefault();
      updateJoystick(element, event.clientX, event.clientY);
    });

    const release = (event) => {
      const state = states.get(vessel);
      if (!state.active) return;
      if (event.pointerId !== undefined && state.pointerId !== event.pointerId) return;
      stopJoystick(element, true);
    };

    element.addEventListener("pointerup", release);
    element.addEventListener("pointercancel", release);
    element.addEventListener("lostpointercapture", release);
  });

  document.getElementById("allStop").addEventListener("click", async () => {
    document.querySelectorAll(".joystick").forEach((element) => {
      stopJoystick(element, false);
    });

    await send("ship", 0, 0);
    await send("target", 0, 0);
    status.textContent = "Both ships stopped.";
  });

  window.addEventListener("blur", () => {
    document.querySelectorAll(".joystick").forEach((element) => {
      stopJoystick(element, true);
    });
  });

  document.addEventListener("visibilitychange", () => {
    if (document.hidden) {
      document.querySelectorAll(".joystick").forEach((element) => {
        stopJoystick(element, true);
      });
    }
  });

  speedSlider.addEventListener("input", updateSliderLabels);
  turnSlider.addEventListener("input", updateSliderLabels);
  updateSliderLabels();
</script>
</body>
</html>
"""


class ShipControlNode(Node):
    def __init__(self) -> None:
        super().__init__("ship_control_panel_node")

        self.ship_publisher = self.create_publisher(
            Twist,
            "/backend/platform_cmd_vel",
            10,
        )

        self.target_publisher = self.create_publisher(
            Twist,
            "/test/target_cmd_vel",
            10,
        )

        self.lock = threading.Lock()

        self.states: Dict[str, dict] = {
            "ship": {
                "forward": 0.0,
                "yaw": 0.0,
                "active": False,
                "last_input": 0.0,
            },
            "target": {
                "forward": 0.0,
                "yaw": 0.0,
                "active": False,
                "last_input": 0.0,
            },
        }

        self.create_timer(PUBLISH_PERIOD, self.publish_loop)

        self.get_logger().info(
            "Ship Control Panel ROS node ready."
        )
        self.get_logger().info(
            "Ship topic: /backend/platform_cmd_vel"
        )
        self.get_logger().info(
            "Target topic: /test/target_cmd_vel"
        )

    @staticmethod
    def clamp(value: float, limit: float) -> float:
        return max(-limit, min(limit, value))

    def set_command(self, vessel: str, forward: float, yaw: float) -> None:
        if vessel not in self.states:
            raise ValueError("Unknown vessel")

        if not math.isfinite(forward) or not math.isfinite(yaw):
            raise ValueError("Non-finite command")

        forward = self.clamp(forward, MAX_FORWARD_SPEED)
        yaw = self.clamp(yaw, MAX_YAW_RATE)

        with self.lock:
            state = self.states[vessel]
            state["forward"] = forward
            state["yaw"] = yaw
            state["last_input"] = time.monotonic()
            state["active"] = (
                abs(forward) > 1e-6
                or abs(yaw) > 1e-6
            )

        if not state["active"]:
            self.publish_zero(vessel)

    def build_message(
        self,
        vessel: str,
        forward: float,
        yaw: float,
    ) -> Twist:
        message = Twist()

        if vessel == "ship":
            # Heybeliada uses its X axis for forward motion.
            message.linear.x = (
                forward * SHIP_FORWARD_SIGN
            )
            message.angular.z = (
                yaw * SHIP_YAW_SIGN
            )
        else:
            # WAM-V target visual forward axis is -Y.
            # Keep X at zero so forward/reverse no longer
            # appears as left/right movement.
            message.linear.x = 0.0
            message.linear.y = (
                -forward * TARGET_FORWARD_SIGN
            )
            message.angular.z = (
                yaw * TARGET_YAW_SIGN
            )

        return message

    def publisher_for(self, vessel: str):
        if vessel == "ship":
            return self.ship_publisher
        return self.target_publisher

    def publish_zero(self, vessel: str) -> None:
        self.publisher_for(vessel).publish(Twist())

    def publish_loop(self) -> None:
        now = time.monotonic()
        commands = []

        with self.lock:
            for vessel, state in self.states.items():
                if not state["active"]:
                    continue

                if now - state["last_input"] > COMMAND_TIMEOUT:
                    state["active"] = False
                    state["forward"] = 0.0
                    state["yaw"] = 0.0
                    commands.append(
                        (vessel, 0.0, 0.0)
                    )
                else:
                    commands.append(
                        (
                            vessel,
                            state["forward"],
                            state["yaw"],
                        )
                    )

        for vessel, forward, yaw in commands:
            message = self.build_message(
                vessel,
                forward,
                yaw,
            )
            self.publisher_for(vessel).publish(message)

    def stop_all(self) -> None:
        with self.lock:
            for state in self.states.values():
                state["active"] = False
                state["forward"] = 0.0
                state["yaw"] = 0.0

        self.publish_zero("ship")
        self.publish_zero("target")


NODE = None


class RequestHandler(BaseHTTPRequestHandler):
    def send_bytes(
        self,
        status: int,
        content_type: str,
        body: bytes,
    ) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header(
            "Content-Length",
            str(len(body)),
        )
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        path = self.path.split("?", 1)[0]

        if path in ("/", "/index.html"):
            body = PAGE.encode("utf-8")
            self.send_bytes(
                200,
                "text/html; charset=utf-8",
                body,
            )
            return

        if path == "/health":
            self.send_bytes(
                200,
                "text/plain; charset=utf-8",
                b"OK\n",
            )
            return

        self.send_bytes(
            404,
            "text/plain; charset=utf-8",
            b"Not found\n",
        )

    def do_POST(self) -> None:
        if self.path != "/command":
            self.send_bytes(
                404,
                "application/json",
                b'{"ok":false}',
            )
            return

        try:
            length = int(
                self.headers.get(
                    "Content-Length",
                    "0",
                )
            )

            if length <= 0 or length > 4096:
                raise ValueError(
                    "Invalid request length"
                )

            payload = json.loads(
                self.rfile.read(length).decode("utf-8")
            )

            vessel = str(payload["vessel"])
            forward = float(payload["forward"])
            yaw = float(payload["yaw"])

            NODE.set_command(
                vessel,
                forward,
                yaw,
            )

            self.send_bytes(
                200,
                "application/json",
                b'{"ok":true}',
            )

        except (
            KeyError,
            ValueError,
            TypeError,
            json.JSONDecodeError,
        ) as error:
            body = json.dumps(
                {
                    "ok": False,
                    "error": str(error),
                }
            ).encode("utf-8")

            self.send_bytes(
                400,
                "application/json",
                body,
            )

        except Exception as error:
            NODE.get_logger().error(
                f"HTTP command error: {error}"
            )

            body = json.dumps(
                {
                    "ok": False,
                    "error": "internal error",
                }
            ).encode("utf-8")

            self.send_bytes(
                500,
                "application/json",
                body,
            )

    def log_message(
        self,
        fmt: str,
        *args,
    ) -> None:
        return


def main() -> None:
    global NODE

    rclpy.init()
    NODE = ShipControlNode()

    spin_thread = threading.Thread(
        target=rclpy.spin,
        args=(NODE,),
        daemon=True,
    )
    spin_thread.start()

    server = ThreadingHTTPServer(
        (HOST, PORT),
        RequestHandler,
    )
    server.daemon_threads = True

    stop_event = threading.Event()

    def request_stop(
        signum=None,
        frame=None,
    ) -> None:
        if stop_event.is_set():
            return

        stop_event.set()

        threading.Thread(
            target=server.shutdown,
            daemon=True,
        ).start()

    signal.signal(
        signal.SIGINT,
        request_stop,
    )
    signal.signal(
        signal.SIGTERM,
        request_stop,
    )

    NODE.get_logger().info(
        f"Ship Control Panel: http://{HOST}:{PORT}"
    )

    try:
        server.serve_forever(
            poll_interval=0.2
        )

    finally:
        NODE.stop_all()
        server.server_close()
        NODE.destroy_node()

        if rclpy.ok():
            rclpy.shutdown()

        spin_thread.join(timeout=2.0)


if __name__ == "__main__":
    main()
