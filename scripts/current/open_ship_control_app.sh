#!/usr/bin/env bash
set -e

PANEL_URL="http://127.0.0.1:8090/?v=2"

# Panel çalışmıyorsa yalnızca yeni Ship Control Panel'i başlat.
if ! curl -fsS "http://127.0.0.1:8090/health" >/dev/null 2>&1; then
    "$HOME/start_ship_control_panel.sh"

    for _ in {1..30}; do
        if curl -fsS "http://127.0.0.1:8090/health" >/dev/null 2>&1; then
            break
        fi
        sleep 0.5
    done
fi

if command -v google-chrome >/dev/null 2>&1; then
    exec google-chrome \
        --app="$PANEL_URL" \
        --class=ShipControlPanel \
        --user-data-dir="$HOME/.cache/ship-control-app"

elif command -v google-chrome-stable >/dev/null 2>&1; then
    exec google-chrome-stable \
        --app="$PANEL_URL" \
        --class=ShipControlPanel \
        --user-data-dir="$HOME/.cache/ship-control-app"

elif command -v chromium >/dev/null 2>&1; then
    exec chromium \
        --app="$PANEL_URL" \
        --class=ShipControlPanel \
        --user-data-dir="$HOME/.cache/ship-control-app"

elif command -v chromium-browser >/dev/null 2>&1; then
    exec chromium-browser \
        --app="$PANEL_URL" \
        --class=ShipControlPanel \
        --user-data-dir="$HOME/.cache/ship-control-app"

else
    exec xdg-open "$PANEL_URL"
fi
