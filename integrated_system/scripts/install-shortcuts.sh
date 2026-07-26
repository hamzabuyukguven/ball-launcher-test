#!/usr/bin/env bash
set -Eeuo pipefail
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

cat > "$HOME/start_ball_launcher_system.sh" <<WRAPPER
#!/usr/bin/env bash
exec "$ROOT_DIR/scripts/start-system.sh" "\$@"
WRAPPER

cat > "$HOME/start_ball_launcher_with_phone.sh" <<WRAPPER
#!/usr/bin/env bash
exec "$ROOT_DIR/scripts/start-system.sh" --with-phone "\$@"
WRAPPER

cat > "$HOME/start_ball_launcher_phone_gun.sh" <<WRAPPER
#!/usr/bin/env bash
exec "$ROOT_DIR/scripts/start-system.sh" --phone-gun-control "\$@"
WRAPPER

cat > "$HOME/stop_ball_launcher_system.sh" <<WRAPPER
#!/usr/bin/env bash
exec "$ROOT_DIR/scripts/stop-system.sh" "\$@"
WRAPPER

chmod +x \
  "$HOME/start_ball_launcher_system.sh" \
  "$HOME/start_ball_launcher_with_phone.sh" \
  "$HOME/start_ball_launcher_phone_gun.sh" \
  "$HOME/stop_ball_launcher_system.sh"

APP_DIR="$HOME/.local/share/applications"
DESKTOP_DIR="$HOME/Desktop"
mkdir -p "$APP_DIR"

create_desktop() {
  local path=$1 name=$2 exec_line=$3
  cat > "$path" <<DESKTOP
[Desktop Entry]
Type=Application
Name=$name
Comment=Ball Launcher integrated system
Exec=$exec_line
Terminal=true
Icon=utilities-terminal
Categories=Development;
DESKTOP
  chmod +x "$path"
  command -v gio >/dev/null 2>&1 && gio set "$path" metadata::trusted true >/dev/null 2>&1 || true
}

create_desktop "$APP_DIR/ball-launcher-system.desktop" \
  "Ball Launcher System" "$HOME/start_ball_launcher_system.sh"
create_desktop "$APP_DIR/ball-launcher-phone.desktop" \
  "Ball Launcher + Phone Control" "$HOME/start_ball_launcher_with_phone.sh"
create_desktop "$APP_DIR/ball-launcher-stop.desktop" \
  "Stop Ball Launcher System" "$HOME/stop_ball_launcher_system.sh"

if [[ -d "$DESKTOP_DIR" ]]; then
  cp "$APP_DIR/ball-launcher-system.desktop" "$DESKTOP_DIR/Ball Launcher System.desktop"
  cp "$APP_DIR/ball-launcher-phone.desktop" "$DESKTOP_DIR/Ball Launcher + Phone Control.desktop"
  cp "$APP_DIR/ball-launcher-stop.desktop" "$DESKTOP_DIR/Stop Ball Launcher System.desktop"
  chmod +x "$DESKTOP_DIR"/*.desktop
  command -v gio >/dev/null 2>&1 && {
    gio set "$DESKTOP_DIR/Ball Launcher System.desktop" metadata::trusted true >/dev/null 2>&1 || true
    gio set "$DESKTOP_DIR/Ball Launcher + Phone Control.desktop" metadata::trusted true >/dev/null 2>&1 || true
    gio set "$DESKTOP_DIR/Stop Ball Launcher System.desktop" metadata::trusted true >/dev/null 2>&1 || true
  }
fi

cat <<DONE
Shortcuts installed:
  ~/start_ball_launcher_system.sh
  ~/start_ball_launcher_with_phone.sh
  ~/start_ball_launcher_phone_gun.sh
  ~/stop_ball_launcher_system.sh

Desktop launchers were also created when ~/Desktop exists.
DONE
