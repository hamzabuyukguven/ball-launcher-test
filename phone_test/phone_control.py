#!/usr/bin/env python3

import json
import math
import threading
import time

import rclpy
from geometry_msgs.msg import Twist
from naval_interfaces.msg import (
    FireCommand,
    GunRateCommand,
    TargetPositionInfo,
)
from rclpy.executors import SingleThreadedExecutor
from rclpy.node import Node
from std_msgs.msg import String
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


HOST = "0.0.0.0"
PORT = 8080

sequence_lock = threading.Lock()
sequence_number = 0

MAX_SHIP_SPEED_MPS = 2.0
MAX_SHIP_YAW_RATE_RAD_S = 0.35
SHIP_COMMAND_TIMEOUT_SEC = 1.50

# Local-only target control. It mirrors the ship joystick dynamics
# but never publishes under /backend/*.
MAX_TARGET_SPEED_MPS = MAX_SHIP_SPEED_MPS
MAX_TARGET_YAW_RATE_RAD_S = MAX_SHIP_YAW_RATE_RAD_S
TARGET_COMMAND_TIMEOUT_SEC = SHIP_COMMAND_TIMEOUT_SEC

DEFAULT_MUZZLE_VELOCITY_MPS = 60.0
TARGET_STALE_TIMEOUT_SEC = 2.0

SHIP_NODE = None


HTML_PAGE = r"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">

    <meta
        name="viewport"
        content="width=device-width, initial-scale=1.0,
                 maximum-scale=1.0, user-scalable=no"
    >

    <title>Heybeliada Control Panel</title>

    <style>
        * {
            box-sizing: border-box;
        }

        body {
            margin: 0;
            padding: 16px;
            background: #0f1720;
            color: #ffffff;
            font-family: Arial, sans-serif;
        }

        .container {
            width: 100%;
            max-width: 980px;
            margin: auto;
        }

        h1 {
            margin: 8px 0 18px;
            text-align: center;
            font-size: 25px;
        }

        h2 {
            margin-top: 0;
            font-size: 19px;
        }

        .card {
            margin-bottom: 16px;
            padding: 17px;
            background: #1e2b36;
            border-radius: 14px;
        }

        .joystick-card-grid {
            display: grid;
            grid-template-columns: repeat(2, minmax(0, 1fr));
            gap: 16px;
            margin-bottom: 16px;
        }

        .joystick-card-grid .card {
            margin-bottom: 0;
        }

        @media (max-width: 760px) {
            .joystick-card-grid {
                grid-template-columns: 1fr;
            }
        }

        label {
            display: block;
            margin-top: 12px;
            margin-bottom: 6px;
            font-weight: bold;
        }

        input {
            width: 100%;
            padding: 12px;
            border: 1px solid #657483;
            border-radius: 9px;
            background: #ffffff;
            color: #000000;
            font-size: 18px;
        }

        button {
            min-height: 52px;
            border: none;
            border-radius: 10px;
            font-size: 17px;
            font-weight: bold;
            touch-action: none;
            cursor: pointer;
        }

        .movement-grid {
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 9px;
        }

        .movement-button {
            background: #2475c7;
            color: white;
        }

        .stop-button {
            background: #e0a800;
            color: #111111;
        }

        .empty {
            visibility: hidden;
        }


        .joystick-shell {
            display: flex;
            flex-direction: column;
            align-items: center;
            gap: 12px;
        }

        .joystick-base {
            position: relative;
            width: min(70vw, 260px);
            height: min(70vw, 260px);
            max-width: 260px;
            max-height: 260px;
            border: 2px solid #71808d;
            border-radius: 50%;
            background:
                radial-gradient(
                    circle at center,
                    #243542 0 31%,
                    #16232d 32% 100%
                );
            touch-action: none;
            user-select: none;
            overflow: hidden;
        }

        .joystick-base::before,
        .joystick-base::after {
            content: "";
            position: absolute;
            background: #536574;
            opacity: 0.55;
            pointer-events: none;
        }

        .joystick-base::before {
            left: 50%;
            top: 8%;
            bottom: 8%;
            width: 2px;
            transform: translateX(-50%);
        }

        .joystick-base::after {
            top: 50%;
            left: 8%;
            right: 8%;
            height: 2px;
            transform: translateY(-50%);
        }

        .joystick-stick {
            position: absolute;
            left: 50%;
            top: 50%;
            width: 88px;
            height: 88px;
            border-radius: 50%;
            border: 2px solid #90bfe5;
            background: #2475c7;
            transform: translate(-50%, -50%);
            pointer-events: none;
        }

        .joystick-readout {
            width: 100%;
            padding: 10px;
            border-radius: 9px;
            background: #0b1117;
            text-align: center;
            white-space: pre-line;
            line-height: 1.4;
        }

        .ship-stop {
            width: 100%;
            background: #e0a800;
            color: #111111;
        }

        .telemetry-status-row {
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 10px;
            margin-bottom: 12px;
        }

        .telemetry-badge {
            display: inline-block;
            min-width: 88px;
            padding: 7px 10px;
            border-radius: 999px;
            background: #455767;
            color: #ffffff;
            text-align: center;
            font-size: 14px;
            font-weight: bold;
        }

        .telemetry-badge.live {
            background: #16856d;
        }

        .telemetry-badge.stale {
            background: #b7791f;
        }

        .telemetry-badge.waiting {
            background: #455767;
        }

        .telemetry-grid {
            display: grid;
            grid-template-columns: repeat(2, minmax(0, 1fr));
            gap: 9px;
        }

        .telemetry-item {
            min-width: 0;
            padding: 11px;
            border-radius: 9px;
            background: #0b1117;
        }

        .telemetry-item.wide {
            grid-column: 1 / -1;
        }

        .telemetry-label {
            margin-bottom: 5px;
            color: #aebdca;
            font-size: 13px;
            font-weight: bold;
        }

        .telemetry-value {
            overflow-wrap: anywhere;
            font-family: monospace;
            font-size: 16px;
        }

        .auto-actions {
            display: grid;
            grid-template-columns: 2fr 1fr;
            gap: 9px;
            margin-top: 14px;
        }

        .auto-fire {
            width: 100%;
            background: #8b3fd1;
            color: #ffffff;
        }

        .auto-cancel {
            width: 100%;
            background: #e0a800;
            color: #111111;
        }

        .auto-status {
            min-height: 92px;
            margin-top: 12px;
            padding: 12px;
            border-radius: 9px;
            background: #0b1117;
            white-space: pre-wrap;
            line-height: 1.4;
        }

        .fire {
            width: 100%;
            margin-top: 14px;
            min-height: 65px;
            background: #d83434;
            color: white;
            font-size: 22px;
        }

        .status {
            min-height: 54px;
            margin-top: 14px;
            padding: 12px;
            border-radius: 9px;
            background: #0b1117;
            white-space: pre-wrap;
            line-height: 1.4;
        }

        .note {
            color: #c3ced8;
            font-size: 14px;
            line-height: 1.4;
        }

        .warning {
            padding: 10px;
            border-left: 4px solid #e0a800;
            background: #28333d;
            color: #e8edf2;
            font-size: 14px;
            line-height: 1.4;
        }
    </style>
</head>

<body>
<div class="container">

    <h1>Heybeliada Control Panel</h1>
    <p class="note" style="text-align:center;">Joystick + Live Target + BALLISTIC AUTO AIM version 4</p>


    <div class="joystick-card-grid">
        <div class="card">
            <h2>Ship Joystick</h2>

            <label for="shipMaxSpeed">
                Maximum Forward / Reverse Speed (m/s)
            </label>
            <input
                id="shipMaxSpeed"
                type="text"
                inputmode="decimal"
                value="1.0"
            >

            <label for="shipMaxTurn">
                Maximum Turn Rate (rad/s)
            </label>
            <input
                id="shipMaxTurn"
                type="text"
                inputmode="decimal"
                value="0.15"
            >

            <p class="note">
                Push up/down for forward/reverse.
                Push left/right to turn.
                Diagonal movement combines speed and turning.
                Releasing the joystick stops the ship.
            </p>

            <div class="joystick-shell">
                <div
                    id="shipJoystick"
                    class="joystick-base"
                    aria-label="Ship movement joystick"
                >
                    <div
                        id="shipJoystickStick"
                        class="joystick-stick"
                    ></div>
                </div>

                <div
                    id="shipJoystickReadout"
                    class="joystick-readout"
                >
                    Forward: 0.00 m/s
                    Turn: 0.000 rad/s
                </div>

                <button
                    class="ship-stop"
                    onclick="releaseShipJoystick(true)"
                >
                    SHIP STOP
                </button>
            </div>
        </div>
        <div class="card">
            <h2>Target Ship Joystick</h2>

            <label for="targetMaxSpeed">
                Maximum Forward / Reverse Speed (m/s)
            </label>
            <input
                id="targetMaxSpeed"
                type="text"
                inputmode="decimal"
                value="1.0"
            >

            <label for="targetMaxTurn">
                Maximum Turn Rate (rad/s)
            </label>
            <input
                id="targetMaxTurn"
                type="text"
                inputmode="decimal"
                value="0.15"
            >

            <p class="note">
                The response, dead zone, limits, send rate and timeout
                are identical to the Ship Joystick. This joystick uses
                only /test/target_cmd_vel and never publishes a backend
                movement command.
            </p>

            <div class="joystick-shell">
                <div
                    id="targetJoystick"
                    class="joystick-base"
                    aria-label="Target ship movement joystick"
                >
                    <div
                        id="targetJoystickStick"
                        class="joystick-stick"
                    ></div>
                </div>

                <div
                    id="targetJoystickReadout"
                    class="joystick-readout"
                >
                    Forward: 0.00 m/s
                    Turn: 0.000 rad/s
                </div>

                <button
                    class="ship-stop"
                    onclick="releaseTargetJoystick(true)"
                >
                    TARGET STOP
                </button>
            </div>
        </div>
    </div>

    <div class="card">
        <h2>Motor Speeds</h2>

        <label for="panRpm">Pan Motor Speed (RPM)</label>
        <input
            id="panRpm"
            type="text"
            inputmode="decimal"
            value="5"
        >

        <label for="tiltRpm">Tilt Motor Speed (RPM)</label>
        <input
            id="tiltRpm"
            type="text"
            inputmode="decimal"
            value="3"
        >

        <p class="note">
            Hold a direction button to move the gun.
            Release the button to stop.
        </p>

        <div class="movement-grid">
            <button class="empty">Empty</button>

            <button
                class="movement-button"
                onpointerdown="startMovement('up', event)"
            >
                UP
            </button>

            <button class="empty">Empty</button>

            <button
                class="movement-button"
                onpointerdown="startMovement('left', event)"
            >
                LEFT
            </button>

            <button
                class="stop-button"
                onclick="stopMovement()"
            >
                STOP
            </button>

            <button
                class="movement-button"
                onpointerdown="startMovement('right', event)"
            >
                RIGHT
            </button>

            <button class="empty">Empty</button>

            <button
                class="movement-button"
                onpointerdown="startMovement('down', event)"
            >
                DOWN
            </button>

            <button class="empty">Empty</button>
        </div>
    </div>

    <div class="card">
        <div class="telemetry-status-row">
            <h2 style="margin:0;">Live Target Telemetry</h2>
            <span
                id="targetTelemetryBadge"
                class="telemetry-badge waiting"
            >
                WAITING
            </span>
        </div>

        <div class="telemetry-grid">
            <div class="telemetry-item wide">
                <div class="telemetry-label">Target ID</div>
                <div
                    id="targetTelemetryId"
                    class="telemetry-value"
                >
                    No target data yet
                </div>
            </div>

            <div class="telemetry-item">
                <div class="telemetry-label">Position X (m)</div>
                <div
                    id="targetTelemetryX"
                    class="telemetry-value"
                >
                    —
                </div>
            </div>

            <div class="telemetry-item">
                <div class="telemetry-label">Position Y (m)</div>
                <div
                    id="targetTelemetryY"
                    class="telemetry-value"
                >
                    —
                </div>
            </div>

            <div class="telemetry-item">
                <div class="telemetry-label">Position Z (m)</div>
                <div
                    id="targetTelemetryZ"
                    class="telemetry-value"
                >
                    —
                </div>
            </div>

            <div class="telemetry-item">
                <div class="telemetry-label">Sequence</div>
                <div
                    id="targetTelemetrySequence"
                    class="telemetry-value"
                >
                    —
                </div>
            </div>

            <div class="telemetry-item wide">
                <div class="telemetry-label">ROS Timestamp</div>
                <div
                    id="targetTelemetryTimestamp"
                    class="telemetry-value"
                >
                    —
                </div>
            </div>

            <div class="telemetry-item wide">
                <div class="telemetry-label">Last Update</div>
                <div
                    id="targetTelemetryAge"
                    class="telemetry-value"
                >
                    Waiting for /simulation/target_position
                </div>
            </div>
        </div>

        <label for="autoMuzzleVelocity">
            AUTO AIM Ballistic Muzzle Velocity (m/s)
        </label>
        <input
            id="autoMuzzleVelocity"
            type="text"
            inputmode="decimal"
            value="60"
        >

        <p class="note">
            This exact value is locked when START is pressed and is
            used both for target interception / ballistic elevation
            and for FireCommand.muzzle_velocity.
        </p>

        <div class="auto-actions">
            <button
                class="auto-fire"
                onclick="startAutoEngagement()"
            >
                AUTO AIM &amp; FIRE (TEST)
            </button>

            <button
                class="auto-cancel"
                onclick="cancelAutoEngagement()"
            >
                CANCEL
            </button>
        </div>

        <div id="autoEngagementStatus" class="auto-status">
            AUTO AIM test controller is idle.
        </div>

        <p class="warning">
            TEST ONLY: Do not send Java backend or manual gun commands
            while AUTO AIM is active. The normal gRPC backend path is
            unchanged and remains the primary system.
        </p>

        <p class="note">
            Target ship information is read continuously from
            /simulation/target_position. This screen no longer sends
            target information.
        </p>
    </div>

    <div class="card">
        <h2>Fire Control</h2>

        <label for="muzzleVelocity">
            Muzzle Velocity (m/s)
        </label>
        <input
            id="muzzleVelocity"
            type="text"
            inputmode="decimal"
            value="60"
        >

        <button
            class="fire"
            onclick="fireGun()"
        >
            FIRE
        </button>

        <div id="status" class="status">
            Phone control panel is ready.
        </div>
    </div>

</div>

<script>
    const statusBox = document.getElementById("status");
    const autoEngagementStatus =
        document.getElementById("autoEngagementStatus");
    const targetTelemetryBadge =
        document.getElementById("targetTelemetryBadge");
    const targetTelemetryId =
        document.getElementById("targetTelemetryId");
    const targetTelemetryX =
        document.getElementById("targetTelemetryX");
    const targetTelemetryY =
        document.getElementById("targetTelemetryY");
    const targetTelemetryZ =
        document.getElementById("targetTelemetryZ");
    const targetTelemetrySequence =
        document.getElementById("targetTelemetrySequence");
    const targetTelemetryTimestamp =
        document.getElementById("targetTelemetryTimestamp");
    const targetTelemetryAge =
        document.getElementById("targetTelemetryAge");

    let movementActive = false;

    const shipJoystick = document.getElementById("shipJoystick");
    const shipJoystickStick =
        document.getElementById("shipJoystickStick");
    const shipJoystickReadout =
        document.getElementById("shipJoystickReadout");

    let shipPointerId = null;
    let shipJoystickActive = false;
    let shipForwardCommand = 0.0;
    let shipTurnCommand = 0.0;
    let shipSendTimer = null;
    let shipRequestInFlight = false;

    const targetJoystick = document.getElementById("targetJoystick");
    const targetJoystickStick =
        document.getElementById("targetJoystickStick");
    const targetJoystickReadout =
        document.getElementById("targetJoystickReadout");

    let targetPointerId = null;
    let targetJoystickActive = false;
    let targetForwardCommand = 0.0;
    let targetTurnCommand = 0.0;
    let targetSendTimer = null;
    let targetRequestInFlight = false;


    function parseNumberFromInput(elementId) {
        const rawValue = document
            .getElementById(elementId)
            .value
            .trim()
            .replace(",", ".");

        const value = Number(rawValue);

        if (!Number.isFinite(value)) {
            throw new Error(
                "Invalid number in " + elementId
            );
        }

        return value;
    }


    async function postJson(path, payload) {
        statusBox.textContent = "Sending command...";

        const response = await fetch(path, {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify(payload)
        });

        const result = await response.json();

        if (!response.ok) {
            throw new Error(
                result.message || "Command failed."
            );
        }

        statusBox.textContent = result.message;
    }


    async function startMovement(direction, event) {
        event.preventDefault();

        try {
            movementActive = true;

            await postJson("/move", {
                direction: direction,
                pan_rpm: parseNumberFromInput("panRpm"),
                tilt_rpm: parseNumberFromInput("tiltRpm")
            });
        } catch (error) {
            movementActive = false;
            statusBox.textContent = "ERROR: " + error.message;
        }
    }


    async function stopMovement() {
        try {
            movementActive = false;
            await postJson("/stop", {});
        } catch (error) {
            statusBox.textContent = "ERROR: " + error.message;
        }
    }




    function clamp(value, minimum, maximum) {
        return Math.max(
            minimum,
            Math.min(maximum, value)
        );
    }


    function updateShipJoystickFromPointer(event) {
        const rectangle =
            shipJoystick.getBoundingClientRect();

        const centerX = rectangle.left
            + rectangle.width / 2.0;
        const centerY = rectangle.top
            + rectangle.height / 2.0;

        const maximumRadius =
            rectangle.width / 2.0 - 46.0;

        let deltaX = event.clientX - centerX;
        let deltaY = event.clientY - centerY;

        const distance = Math.hypot(
            deltaX,
            deltaY
        );

        if (distance > maximumRadius) {
            const scale =
                maximumRadius / distance;

            deltaX *= scale;
            deltaY *= scale;
        }

        shipJoystickStick.style.left =
            `calc(50% + ${deltaX}px)`;
        shipJoystickStick.style.top =
            `calc(50% + ${deltaY}px)`;

        let normalizedX =
            deltaX / maximumRadius;
        let normalizedY =
            deltaY / maximumRadius;

        const deadZone = 0.08;

        if (Math.abs(normalizedX) < deadZone) {
            normalizedX = 0.0;
        }

        if (Math.abs(normalizedY) < deadZone) {
            normalizedY = 0.0;
        }

        const maximumSpeed = Math.abs(
            parseNumberFromInput("shipMaxSpeed")
        );

        const maximumTurn = Math.abs(
            parseNumberFromInput("shipMaxTurn")
        );

        // Screen up is negative Y, therefore negate it
        // to make upward joystick movement positive forward.
        shipForwardCommand = clamp(
            -normalizedY * maximumSpeed,
            -2.0,
            2.0
        );

        // ROS positive angular Z turns left. Dragging right
        // should turn right, so horizontal command is negated.
        shipTurnCommand = clamp(
            -normalizedX * maximumTurn,
            -0.35,
            0.35
        );

        shipJoystickReadout.textContent =
            "Forward: "
            + shipForwardCommand.toFixed(2)
            + " m/s\nTurn: "
            + shipTurnCommand.toFixed(3)
            + " rad/s";
    }


    async function sendShipJoystickCommand(
        showStatus = false
    ) {
        if (shipRequestInFlight) {
            return;
        }

        shipRequestInFlight = true;

        try {
            const response = await fetch(
                "/ship/joystick",
                {
                    method: "POST",
                    headers: {
                        "Content-Type":
                            "application/json"
                    },
                    body: JSON.stringify({
                        forward_mps:
                            shipForwardCommand,
                        yaw_rate_rad_s:
                            shipTurnCommand
                    })
                }
            );

            const result =
                await response.json();

            if (!response.ok) {
                throw new Error(
                    result.message
                    || "Ship command failed."
                );
            }

            if (showStatus) {
                statusBox.textContent =
                    result.message;
            }
        } catch (error) {
            statusBox.textContent =
                "ERROR: " + error.message;
            releaseShipJoystick(false);
        } finally {
            shipRequestInFlight = false;
        }
    }


    function startShipJoystick(event) {
        event.preventDefault();

        shipPointerId = event.pointerId;
        shipJoystickActive = true;

        shipJoystick.setPointerCapture(
            event.pointerId
        );

        updateShipJoystickFromPointer(event);
        sendShipJoystickCommand(true);

        clearInterval(shipSendTimer);
        shipSendTimer = setInterval(
            () => {
                if (shipJoystickActive) {
                    sendShipJoystickCommand(false);
                }
            },
            100
        );
    }


    function moveShipJoystick(event) {
        if (
            !shipJoystickActive
            || event.pointerId !== shipPointerId
        ) {
            return;
        }

        event.preventDefault();
        updateShipJoystickFromPointer(event);
    }


    function releaseShipJoystick(showStatus = true) {
        clearInterval(shipSendTimer);
        shipSendTimer = null;

        shipJoystickActive = false;
        shipPointerId = null;
        shipForwardCommand = 0.0;
        shipTurnCommand = 0.0;

        shipJoystickStick.style.left = "50%";
        shipJoystickStick.style.top = "50%";

        shipJoystickReadout.textContent =
            "Forward: 0.00 m/s\n"
            + "Turn: 0.000 rad/s";

        sendShipJoystickCommand(showStatus);
    }


    shipJoystick.addEventListener(
        "pointerdown",
        startShipJoystick
    );

    shipJoystick.addEventListener(
        "pointermove",
        moveShipJoystick
    );

    shipJoystick.addEventListener(
        "pointerup",
        () => releaseShipJoystick(true)
    );

    shipJoystick.addEventListener(
        "pointercancel",
        () => releaseShipJoystick(true)
    );


    function updateTargetJoystickFromPointer(event) {
        const rectangle =
            targetJoystick.getBoundingClientRect();

        const centerX = rectangle.left
            + rectangle.width / 2.0;
        const centerY = rectangle.top
            + rectangle.height / 2.0;

        const maximumRadius =
            rectangle.width / 2.0 - 46.0;

        let deltaX = event.clientX - centerX;
        let deltaY = event.clientY - centerY;

        const distance = Math.hypot(
            deltaX,
            deltaY
        );

        if (distance > maximumRadius) {
            const scale = maximumRadius / distance;
            deltaX *= scale;
            deltaY *= scale;
        }

        targetJoystickStick.style.left =
            `calc(50% + ${deltaX}px)`;
        targetJoystickStick.style.top =
            `calc(50% + ${deltaY}px)`;

        let normalizedX = deltaX / maximumRadius;
        let normalizedY = deltaY / maximumRadius;

        const deadZone = 0.08;

        if (Math.abs(normalizedX) < deadZone) {
            normalizedX = 0.0;
        }

        if (Math.abs(normalizedY) < deadZone) {
            normalizedY = 0.0;
        }

        const maximumSpeed = Math.abs(
            parseNumberFromInput("targetMaxSpeed")
        );

        const maximumTurn = Math.abs(
            parseNumberFromInput("targetMaxTurn")
        );

        // Identical mapping to the main ship joystick.
        targetForwardCommand = clamp(
            -normalizedY * maximumSpeed,
            -2.0,
            2.0
        );

        targetTurnCommand = clamp(
            -normalizedX * maximumTurn,
            -0.35,
            0.35
        );

        targetJoystickReadout.textContent =
            "Forward: "
            + targetForwardCommand.toFixed(2)
            + " m/s\nTurn: "
            + targetTurnCommand.toFixed(3)
            + " rad/s";
    }


    async function sendTargetJoystickCommand(
        showStatus = false
    ) {
        if (targetRequestInFlight) {
            return;
        }

        targetRequestInFlight = true;

        try {
            const response = await fetch(
                "/target/joystick",
                {
                    method: "POST",
                    headers: {
                        "Content-Type":
                            "application/json"
                    },
                    body: JSON.stringify({
                        forward_mps:
                            targetForwardCommand,
                        yaw_rate_rad_s:
                            targetTurnCommand
                    })
                }
            );

            const result = await response.json();

            if (!response.ok) {
                throw new Error(
                    result.message
                    || "Target command failed."
                );
            }

            if (showStatus) {
                statusBox.textContent = result.message;
            }
        } catch (error) {
            statusBox.textContent =
                "ERROR: " + error.message;
            releaseTargetJoystick(false);
        } finally {
            targetRequestInFlight = false;
        }
    }


    function startTargetJoystick(event) {
        event.preventDefault();
        targetPointerId = event.pointerId;
        targetJoystickActive = true;
        targetJoystick.setPointerCapture(event.pointerId);
        updateTargetJoystickFromPointer(event);
        sendTargetJoystickCommand(true);

        clearInterval(targetSendTimer);
        targetSendTimer = setInterval(
            () => {
                if (targetJoystickActive) {
                    sendTargetJoystickCommand(false);
                }
            },
            100
        );
    }


    function moveTargetJoystick(event) {
        if (
            !targetJoystickActive
            || event.pointerId !== targetPointerId
        ) {
            return;
        }

        event.preventDefault();
        updateTargetJoystickFromPointer(event);
    }


    function releaseTargetJoystick(showStatus = true) {
        clearInterval(targetSendTimer);
        targetSendTimer = null;
        targetJoystickActive = false;
        targetPointerId = null;
        targetForwardCommand = 0.0;
        targetTurnCommand = 0.0;

        targetJoystickStick.style.left = "50%";
        targetJoystickStick.style.top = "50%";
        targetJoystickReadout.textContent =
            "Forward: 0.00 m/s\n"
            + "Turn: 0.000 rad/s";

        sendTargetJoystickCommand(showStatus);
    }


    targetJoystick.addEventListener(
        "pointerdown",
        startTargetJoystick
    );

    targetJoystick.addEventListener(
        "pointermove",
        moveTargetJoystick
    );

    targetJoystick.addEventListener(
        "pointerup",
        () => releaseTargetJoystick(true)
    );

    targetJoystick.addEventListener(
        "pointercancel",
        () => releaseTargetJoystick(true)
    );


    function setTargetTelemetryWaiting(message) {
        targetTelemetryBadge.textContent = "WAITING";
        targetTelemetryBadge.className =
            "telemetry-badge waiting";
        targetTelemetryId.textContent =
            "No target data yet";
        targetTelemetryX.textContent = "—";
        targetTelemetryY.textContent = "—";
        targetTelemetryZ.textContent = "—";
        targetTelemetrySequence.textContent = "—";
        targetTelemetryTimestamp.textContent = "—";
        targetTelemetryAge.textContent = message;
    }


    async function refreshTargetTelemetry() {
        try {
            const response = await fetch(
                "/api/target",
                {
                    method: "GET",
                    cache: "no-store"
                }
            );

            const result = await response.json();

            if (!response.ok) {
                throw new Error(
                    result.message
                    || "Target telemetry request failed."
                );
            }

            if (!result.available) {
                setTargetTelemetryWaiting(
                    "Waiting for /simulation/target_position"
                );
                return;
            }

            if (result.stale) {
                targetTelemetryBadge.textContent = "STALE";
                targetTelemetryBadge.className =
                    "telemetry-badge stale";
            } else {
                targetTelemetryBadge.textContent = "LIVE";
                targetTelemetryBadge.className =
                    "telemetry-badge live";
            }

            targetTelemetryId.textContent =
                result.target_id;
            targetTelemetryX.textContent =
                Number(result.position_x).toFixed(4);
            targetTelemetryY.textContent =
                Number(result.position_y).toFixed(4);
            targetTelemetryZ.textContent =
                Number(result.position_z).toFixed(4);
            targetTelemetrySequence.textContent =
                String(result.sequence);

            const nanosecondText = String(
                result.timestamp_nanosec
            ).padStart(9, "0");

            targetTelemetryTimestamp.textContent =
                String(result.timestamp_sec)
                + "."
                + nanosecondText;

            targetTelemetryAge.textContent =
                Number(result.age_sec).toFixed(2)
                + " seconds ago";
        } catch (error) {
            targetTelemetryBadge.textContent = "ERROR";
            targetTelemetryBadge.className =
                "telemetry-badge stale";
            targetTelemetryAge.textContent =
                "ERROR: " + error.message;
        }
    }


    async function startAutoEngagement() {
        try {
            await postJson("/auto/start", {
                muzzle_velocity:
                    parseNumberFromInput(
                        "autoMuzzleVelocity"
                    )
            });
            refreshAutoEngagementStatus();
        } catch (error) {
            statusBox.textContent =
                "ERROR: " + error.message;
        }
    }


    async function cancelAutoEngagement() {
        try {
            await postJson("/auto/cancel", {});
            refreshAutoEngagementStatus();
        } catch (error) {
            statusBox.textContent =
                "ERROR: " + error.message;
        }
    }


    async function refreshAutoEngagementStatus() {
        try {
            const response = await fetch(
                "/api/auto-status",
                {
                    method: "GET",
                    cache: "no-store"
                }
            );
            const result = await response.json();

            if (!response.ok) {
                throw new Error(
                    result.message
                    || "AUTO AIM status failed."
                );
            }

            let text =
                "State: " + result.state
                + "\n" + result.message;

            if (
                Number.isFinite(
                    Number(
                        result.solution_muzzle_velocity
                    )
                )
            ) {
                text +=
                    "\nBallistic + fire speed: "
                    + Number(
                        result.solution_muzzle_velocity
                    ).toFixed(2)
                    + " m/s";
            }

            if (
                Number.isFinite(
                    Number(result.target_aim_offset_z)
                )
            ) {
                text +=
                    "\nTarget aim height offset: "
                    + Number(
                        result.target_aim_offset_z
                    ).toFixed(2)
                    + " m";
            }

            if (
                Number.isFinite(
                    Number(result.predicted_miss_m)
                )
            ) {
                text +=
                    "\nSolver residual: "
                    + Number(
                        result.predicted_miss_m
                    ).toFixed(4)
                    + " m";
            }

            if (result.geometry_source) {
                const parts =
                    String(result.geometry_source)
                    .split("/");
                text +=
                    "\nGeometry: "
                    + parts[parts.length - 2]
                    + "/"
                    + parts[parts.length - 1];
            }

            if (
                Number.isFinite(
                    Number(result.pan_error_deg)
                )
            ) {
                text +=
                    "\nPan error: "
                    + Number(
                        result.pan_error_deg
                    ).toFixed(2)
                    + "°";
            }

            if (
                Number.isFinite(
                    Number(result.tilt_error_deg)
                )
            ) {
                text +=
                    "\nTilt error: "
                    + Number(
                        result.tilt_error_deg
                    ).toFixed(2)
                    + "°";
            }

            if (
                Number.isFinite(
                    Number(result.horizontal_range)
                )
            ) {
                text +=
                    "\nRange: "
                    + Number(
                        result.horizontal_range
                    ).toFixed(2)
                    + " m";
            }

            if (
                Number.isFinite(
                    Number(result.flight_time)
                )
            ) {
                text +=
                    "\nFlight time: "
                    + Number(
                        result.flight_time
                    ).toFixed(2)
                    + " s";
            }

            autoEngagementStatus.textContent = text;
        } catch (error) {
            autoEngagementStatus.textContent =
                "AUTO AIM status unavailable: "
                + error.message;
        }
    }


    async function fireGun() {
        try {
            await postJson("/fire", {
                muzzle_velocity:
                    parseNumberFromInput("muzzleVelocity")
            });
        } catch (error) {
            statusBox.textContent =
                "ERROR: " + error.message;
        }
    }



    window.addEventListener("pointerup", () => {
        if (movementActive) {
            stopMovement();
        }
    });


    window.addEventListener("pointercancel", () => {
        if (movementActive) {
            stopMovement();
        }
    });


    window.addEventListener("blur", () => {
        if (movementActive) {
            stopMovement();
        }

        if (shipJoystickActive) {
            releaseShipJoystick(false);
        }

        if (targetJoystickActive) {
            releaseTargetJoystick(false);
        }
    });

    document.addEventListener(
        "visibilitychange",
        () => {
            if (
                document.hidden
                && shipJoystickActive
            ) {
                releaseShipJoystick(false);
            }

            if (
                document.hidden
                && targetJoystickActive
            ) {
                releaseTargetJoystick(false);
            }
        }
    );

    refreshTargetTelemetry();
    setInterval(refreshTargetTelemetry, 500);

    refreshAutoEngagementStatus();
    setInterval(refreshAutoEngagementStatus, 500);
</script>
</body>
</html>
"""



class ShipCommandNode(Node):

    def __init__(self):
        super().__init__("phone_ship_joystick_node")

        self.publisher = self.create_publisher(
            Twist,
            "/backend/platform_cmd_vel",
            10,
        )
        self.target_velocity_publisher = self.create_publisher(
            Twist,
            "/test/target_cmd_vel",
            10,
        )
        self.gun_rate_publisher = self.create_publisher(
            GunRateCommand,
            "/backend/gun_rate_command",
            10,
        )
        self.fire_publisher = self.create_publisher(
            FireCommand,
            "/backend/fire_command",
            10,
        )
        self.target_subscription = self.create_subscription(
            TargetPositionInfo,
            "/simulation/target_position",
            self.target_position_callback,
            10,
        )
        self.auto_command_publisher = self.create_publisher(
            String,
            "/test/auto_engage_command",
            10,
        )
        self.auto_status_subscription = self.create_subscription(
            String,
            "/test/auto_engage_status",
            self.auto_status_callback,
            10,
        )

        self.command_lock = threading.Lock()
        self.forward_mps = 0.0
        self.yaw_rate_rad_s = 0.0
        self.last_update_time = time.monotonic()

        self.target_command_lock = threading.Lock()
        self.target_forward_mps = 0.0
        self.target_yaw_rate_rad_s = 0.0
        self.last_target_command_time = time.monotonic()

        self.target_lock = threading.Lock()
        self.latest_target = None
        self.last_target_received_time = None

        self.auto_status_lock = threading.Lock()
        self.latest_auto_status = {
            "state": "IDLE",
            "active": False,
            "message":
                "AUTO AIM test controller is idle.",
            "backend_safe": True,
        }

        self.create_timer(
            0.05,
            self.publish_current_command,
        )
        self.create_timer(
            0.05,
            self.publish_current_target_command,
        )

        self.get_logger().info(
            "Ship joystick publisher ready: "
            "/backend/platform_cmd_vel"
        )
        self.get_logger().info(
            "Local target joystick publisher ready: "
            "/test/target_cmd_vel"
        )
        self.get_logger().info(
            "Gun movement publisher ready: "
            "/backend/gun_rate_command"
        )
        self.get_logger().info(
            "Fire publisher ready: "
            "/backend/fire_command"
        )
        self.get_logger().info(
            "Target subscriber ready: "
            "/simulation/target_position"
        )
        self.get_logger().info(
            "AUTO AIM test command publisher ready: "
            "/test/auto_engage_command"
        )
        self.get_logger().info(
            "AUTO AIM test status subscriber ready: "
            "/test/auto_engage_status"
        )

    def auto_status_callback(self, message):
        try:
            payload = json.loads(message.data)
        except json.JSONDecodeError:
            payload = {
                "state": "ERROR",
                "active": False,
                "message": message.data,
                "backend_safe": True,
            }

        with self.auto_status_lock:
            self.latest_auto_status = payload

    def get_auto_status_snapshot(self):
        with self.auto_status_lock:
            return dict(self.latest_auto_status)

    def start_auto_engagement(
        self,
        muzzle_velocity,
    ):
        muzzle_velocity = float(muzzle_velocity)

        if (
            not math.isfinite(muzzle_velocity)
            or muzzle_velocity <= 0.0
        ):
            raise ValueError(
                "AUTO AIM muzzle velocity must be positive."
            )

        message = String()
        message.data = json.dumps({
            "action": "START",
            "muzzle_velocity": muzzle_velocity,
        })
        self.auto_command_publisher.publish(message)

    def cancel_auto_engagement(self):
        message = String()
        message.data = json.dumps({
            "action": "CANCEL",
        })
        self.auto_command_publisher.publish(message)

    def target_position_callback(
        self,
        message,
    ):
        snapshot = {
            "sequence": int(message.sequence),
            "target_id": str(message.target_id),
            "position_x": float(message.position_x),
            "position_y": float(message.position_y),
            "position_z": float(message.position_z),
            "timestamp_sec": int(message.timestamp.sec),
            "timestamp_nanosec": int(
                message.timestamp.nanosec
            ),
        }

        with self.target_lock:
            self.latest_target = snapshot
            self.last_target_received_time = (
                time.monotonic()
            )

    def get_target_snapshot(self):
        now = time.monotonic()

        with self.target_lock:
            if (
                self.latest_target is None
                or self.last_target_received_time is None
            ):
                return {
                    "available": False,
                    "stale": True,
                }

            snapshot = dict(self.latest_target)
            age_sec = max(
                0.0,
                now - self.last_target_received_time,
            )

        snapshot["available"] = True
        snapshot["age_sec"] = age_sec
        snapshot["stale"] = (
            age_sec > TARGET_STALE_TIMEOUT_SEC
        )
        return snapshot

    def publish_gun_rate(
        self,
        pan_rpm,
        tilt_rpm,
        control_enabled=True,
    ):
        pan_rate = rpm_to_rad_s(pan_rpm)
        tilt_rate = rpm_to_rad_s(tilt_rpm)

        if (
            not math.isfinite(pan_rate)
            or not math.isfinite(tilt_rate)
        ):
            raise ValueError(
                "Gun command must contain finite numbers."
            )

        message = GunRateCommand()
        message.sequence = next_sequence()
        message.pan_rate = float(pan_rate)
        message.tilt_rate = float(tilt_rate)
        message.control_enabled = bool(control_enabled)
        message.timestamp = (
            self.get_clock().now().to_msg()
        )

        self.gun_rate_publisher.publish(message)
        return pan_rate, tilt_rate

    def publish_fire(self, muzzle_velocity):
        muzzle_velocity = float(muzzle_velocity)

        if (
            not math.isfinite(muzzle_velocity)
            or muzzle_velocity <= 0.0
        ):
            raise ValueError(
                "Muzzle velocity must be positive."
            )

        message = FireCommand()
        message.sequence = next_sequence()
        message.muzzle_velocity = muzzle_velocity
        message.timestamp = (
            self.get_clock().now().to_msg()
        )

        self.fire_publisher.publish(message)
        return muzzle_velocity

    @staticmethod
    def clamp(value, minimum, maximum):
        return max(
            minimum,
            min(maximum, value),
        )

    def set_command(
        self,
        forward_mps,
        yaw_rate_rad_s,
    ):
        forward_mps = float(forward_mps)
        yaw_rate_rad_s = float(
            yaw_rate_rad_s
        )

        if (
            not math.isfinite(forward_mps)
            or not math.isfinite(
                yaw_rate_rad_s
            )
        ):
            raise ValueError(
                "Ship command must contain "
                "finite numbers."
            )

        with self.command_lock:
            self.forward_mps = self.clamp(
                forward_mps,
                -MAX_SHIP_SPEED_MPS,
                MAX_SHIP_SPEED_MPS,
            )
            self.yaw_rate_rad_s = self.clamp(
                yaw_rate_rad_s,
                -MAX_SHIP_YAW_RATE_RAD_S,
                MAX_SHIP_YAW_RATE_RAD_S,
            )
            self.last_update_time = (
                time.monotonic()
            )

    def stop_target(self):
        self.set_target_command(0.0, 0.0)
        self.publish_target_twist(0.0, 0.0)

    def stop(self):
        # Process shutdown safety: stop both independently controlled ships.
        self.set_command(0.0, 0.0)
        self.publish_twist(0.0, 0.0)
        self.stop_target()

    def publish_twist(
        self,
        forward_mps,
        yaw_rate_rad_s,
    ):
        message = Twist()
        message.linear.x = float(
            forward_mps
        )
        message.linear.y = 0.0
        message.linear.z = 0.0
        message.angular.x = 0.0
        message.angular.y = 0.0
        message.angular.z = float(
            yaw_rate_rad_s
        )

        self.publisher.publish(message)

    def publish_current_command(self):
        now = time.monotonic()

        with self.command_lock:
            elapsed = (
                now - self.last_update_time
            )

            if (
                elapsed
                > SHIP_COMMAND_TIMEOUT_SEC
            ):
                self.forward_mps = 0.0
                self.yaw_rate_rad_s = 0.0

            forward_mps = self.forward_mps
            yaw_rate_rad_s = (
                self.yaw_rate_rad_s
            )

        self.publish_twist(
            forward_mps,
            yaw_rate_rad_s,
        )


    def set_target_command(
        self,
        forward_mps,
        yaw_rate_rad_s,
    ):
        forward_mps = float(forward_mps)
        yaw_rate_rad_s = float(yaw_rate_rad_s)

        if (
            not math.isfinite(forward_mps)
            or not math.isfinite(yaw_rate_rad_s)
        ):
            raise ValueError(
                "Target command must contain finite numbers."
            )

        with self.target_command_lock:
            self.target_forward_mps = self.clamp(
                forward_mps,
                -MAX_TARGET_SPEED_MPS,
                MAX_TARGET_SPEED_MPS,
            )
            self.target_yaw_rate_rad_s = self.clamp(
                yaw_rate_rad_s,
                -MAX_TARGET_YAW_RATE_RAD_S,
                MAX_TARGET_YAW_RATE_RAD_S,
            )
            self.last_target_command_time = time.monotonic()

    def publish_target_twist(
        self,
        forward_mps,
        yaw_rate_rad_s,
    ):
        message = Twist()
        # Roussen mesh'inin görsel ileri yönü -Y eksenidir.
        # Ana geminin hız büyüklüğü ve joystick dinamikleri korunur;
        # yalnızca target modelinin eksen eşlemesi düzeltilir.
        message.linear.x = 0.0
        message.linear.y = -float(forward_mps)
        message.linear.z = 0.0
        message.angular.x = 0.0
        message.angular.y = 0.0
        message.angular.z = float(yaw_rate_rad_s)
        self.target_velocity_publisher.publish(message)

    def publish_current_target_command(self):
        now = time.monotonic()

        with self.target_command_lock:
            elapsed = now - self.last_target_command_time

            if elapsed > TARGET_COMMAND_TIMEOUT_SEC:
                self.target_forward_mps = 0.0
                self.target_yaw_rate_rad_s = 0.0

            forward_mps = self.target_forward_mps
            yaw_rate_rad_s = self.target_yaw_rate_rad_s

        self.publish_target_twist(
            forward_mps,
            yaw_rate_rad_s,
        )


def next_sequence():
    global sequence_number

    with sequence_lock:
        sequence_number += 1
        return sequence_number



def rpm_to_rad_s(rpm):
    return float(rpm) * 2.0 * math.pi / 60.0



class PhoneControlHandler(BaseHTTPRequestHandler):

    def send_json(self, status_code, payload):
        body = json.dumps(
            payload,
            ensure_ascii=False
        ).encode("utf-8")

        self.send_response(status_code)
        self.send_header(
            "Content-Type",
            "application/json; charset=utf-8"
        )
        self.send_header(
            "Content-Length",
            str(len(body))
        )
        self.end_headers()

        self.wfile.write(body)


    def do_GET(self):
        request_path = self.path.split("?", 1)[0]

        if request_path == "/api/auto-status":
            if SHIP_NODE is None:
                self.send_json(503, {
                    "message":
                        "ROS node is not ready."
                })
                return

            self.send_json(
                200,
                SHIP_NODE.get_auto_status_snapshot(),
            )
            return

        if request_path == "/api/target":
            if SHIP_NODE is None:
                self.send_json(503, {
                    "message":
                        "ROS node is not ready."
                })
                return

            self.send_json(
                200,
                SHIP_NODE.get_target_snapshot(),
            )
            return

        if request_path != "/":
            self.send_error(404)
            return

        page = HTML_PAGE.encode("utf-8")

        self.send_response(200)
        self.send_header(
            "Content-Type",
            "text/html; charset=utf-8"
        )
        self.send_header(
            "Cache-Control",
            "no-store, no-cache, must-revalidate"
        )
        self.send_header(
            "Pragma",
            "no-cache"
        )
        self.send_header(
            "Content-Length",
            str(len(page))
        )
        self.end_headers()

        self.wfile.write(page)


    def do_POST(self):
        try:
            content_length = int(
                self.headers.get("Content-Length", "0")
            )

            raw_body = self.rfile.read(content_length)

            if raw_body:
                data = json.loads(
                    raw_body.decode("utf-8")
                )
            else:
                data = {}

            if self.path == "/move":
                self.handle_move(data)
                return

            if self.path == "/stop":
                self.handle_stop()
                return

            if self.path == "/ship/joystick":
                self.handle_ship_joystick(data)
                return

            if self.path == "/target/joystick":
                self.handle_target_joystick(data)
                return

            if self.path == "/auto/start":
                self.handle_auto_start(data)
                return

            if self.path == "/auto/cancel":
                self.handle_auto_cancel()
                return

            if self.path == "/fire":
                self.handle_fire(data)
                return

            self.send_json(404, {
                "message": "Unknown command."
            })

        except Exception as error:
            self.send_json(500, {
                "message": str(error)
            })


    def handle_move(self, data):
        direction = str(
            data.get("direction", "")
        ).lower()

        pan_speed = abs(
            float(data.get("pan_rpm", 0.0))
        )

        tilt_speed = abs(
            float(data.get("tilt_rpm", 0.0))
        )

        pan_rpm = 0.0
        tilt_rpm = 0.0

        if direction == "left":
            pan_rpm = -pan_speed

        elif direction == "right":
            pan_rpm = pan_speed

        elif direction == "up":
            tilt_rpm = tilt_speed

        elif direction == "down":
            tilt_rpm = -tilt_speed

        else:
            raise ValueError(
                "Invalid movement direction."
            )

        if SHIP_NODE is None:
            raise RuntimeError(
                "ROS node is not ready."
            )

        pan_rad_s, tilt_rad_s = (
            SHIP_NODE.publish_gun_rate(
                pan_rpm=pan_rpm,
                tilt_rpm=tilt_rpm,
                control_enabled=True,
            )
        )

        self.send_json(200, {
            "message": (
                f"Moving {direction.upper()}\n"
                f"Pan rate: {pan_rad_s:.4f} rad/s\n"
                f"Tilt rate: {tilt_rad_s:.4f} rad/s"
            )
        })


    def handle_stop(self):
        if SHIP_NODE is None:
            raise RuntimeError(
                "ROS node is not ready."
            )

        SHIP_NODE.publish_gun_rate(
            pan_rpm=0.0,
            tilt_rpm=0.0,
            control_enabled=True,
        )

        self.send_json(200, {
            "message": "Gun movement stopped."
        })



    def handle_ship_joystick(self, data):
        forward_mps = float(
            data.get("forward_mps", 0.0)
        )
        yaw_rate_rad_s = float(
            data.get("yaw_rate_rad_s", 0.0)
        )

        if SHIP_NODE is None:
            raise RuntimeError(
                "Ship joystick ROS node "
                "is not ready."
            )

        SHIP_NODE.set_command(
            forward_mps,
            yaw_rate_rad_s,
        )

        self.send_json(200, {
            "message": (
                "Ship joystick active.\n"
                f"Forward: {forward_mps:.2f} m/s\n"
                f"Turn: {yaw_rate_rad_s:.3f} rad/s"
            )
        })


    def handle_target_joystick(self, data):
        forward_mps = float(
            data.get("forward_mps", 0.0)
        )
        yaw_rate_rad_s = float(
            data.get("yaw_rate_rad_s", 0.0)
        )

        if SHIP_NODE is None:
            raise RuntimeError(
                "Target joystick ROS node is not ready."
            )

        SHIP_NODE.set_target_command(
            forward_mps,
            yaw_rate_rad_s,
        )

        self.send_json(200, {
            "message": (
                "Target joystick active (local only).\n"
                f"Forward: {forward_mps:.2f} m/s\n"
                f"Turn: {yaw_rate_rad_s:.3f} rad/s\n"
                "No backend movement topic was used."
            )
        })


    def handle_auto_start(self, data):
        if SHIP_NODE is None:
            raise RuntimeError(
                "ROS node is not ready."
            )

        muzzle_velocity = float(
            data.get(
                "muzzle_velocity",
                DEFAULT_MUZZLE_VELOCITY_MPS,
            )
        )
        SHIP_NODE.start_auto_engagement(
            muzzle_velocity
        )

        self.send_json(200, {
            "message": (
                "AUTO AIM & FIRE test started.\n"
                "Do not send backend/manual gun commands "
                "until it completes or is cancelled."
            )
        })

    def handle_auto_cancel(self):
        if SHIP_NODE is None:
            raise RuntimeError(
                "ROS node is not ready."
            )

        SHIP_NODE.cancel_auto_engagement()

        self.send_json(200, {
            "message":
                "AUTO AIM test cancel command sent."
        })

    def handle_fire(self, data):
        if SHIP_NODE is None:
            raise RuntimeError(
                "ROS node is not ready."
            )

        muzzle_velocity = float(
            data.get(
                "muzzle_velocity",
                DEFAULT_MUZZLE_VELOCITY_MPS,
            )
        )

        actual_velocity = SHIP_NODE.publish_fire(
            muzzle_velocity
        )

        self.send_json(200, {
            "message": (
                "Fire command sent successfully.\n"
                f"Muzzle velocity: "
                f"{actual_velocity:.2f} m/s"
            )
        })


    def log_message(self, format_string, *args):
        print(
            f"{self.client_address[0]} - "
            f"{format_string % args}"
        )


if __name__ == "__main__":
    rclpy.init()

    SHIP_NODE = ShipCommandNode()

    executor = SingleThreadedExecutor()
    executor.add_node(SHIP_NODE)

    executor_thread = threading.Thread(
        target=executor.spin,
        daemon=True,
    )
    executor_thread.start()

    server = ThreadingHTTPServer(
        (HOST, PORT),
        PhoneControlHandler
    )

    print("=" * 62)
    print("Heybeliada phone control server is running")
    print(f"Address: http://0.0.0.0:{PORT}")
    print("Version: dual-identical-joystick-target-auto-5")
    print("Gun control: direct ROS 2 v5 publishers")
    print("Ship control: 20 Hz ROS joystick publisher")
    print("Target control: local /test/target_cmd_vel only")
    print("Target display: /simulation/target_position")
    print("AUTO AIM TEST: /test/auto_engage_command")
    print("Press Ctrl+C to stop")
    print("=" * 62)

    try:
        server.serve_forever()

    except KeyboardInterrupt:
        print("\nServer is shutting down...")

    finally:
        try:
            SHIP_NODE.stop()
            time.sleep(0.10)
        except Exception as error:
            print(f"Ship stop error: {error}")

        server.server_close()
        executor.shutdown()
        SHIP_NODE.destroy_node()

        if rclpy.ok():
            rclpy.shutdown()

        executor_thread.join(timeout=2.0)
