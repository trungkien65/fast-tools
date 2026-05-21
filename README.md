# Fast Tools

Fast Tools is a Python 3.12 / PySide6 desktop app for Ubuntu that checks common developer packages and installs selected packages through `pkexec apt install -y`.

The GUI does not need to run as root. `pkexec` will ask for authorization only when installation is requested.

## Tools

Tool definitions live in `app/config/tools.json`. Edit that file to add, remove, or rename packages.

Each tool supports these fields:

```json
{
  "name": "Redis",
  "package": "redis-server",
  "service": "redis-server",
  "category": "database",
  "command": "redis-server",
  "description": "Redis in-memory data store"
}
```

Default packages:

- `mysql-server`
- `mysql-client`
- `redis-server`
- `nginx`
- `postgresql`
- `docker.io`
- `git`
- `curl`
- `wget`
- `code`

`code` requires the Microsoft apt repository. Without that repository, Fast Tools will show `Package not found`.

## Local Run On Ubuntu

```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m app.main
```

Package status checks use:

```bash
dpkg-query -W -f=${Status} <package>
dpkg-query -W -f=${Status}\t${Version} <package>
apt-cache show <package>
```

Installation uses:

```bash
pkexec apt install -y <package>
```

If `pkexec` is not available, the installer falls back to:

```bash
sudo apt install -y <package>
```

Service checks use `systemctl is-active` and `systemctl is-enabled` for tools that define a `service` field. Service control helpers are available in `app/core/service_manager.py`.

## Current Feature Set

- Config-driven tools list with `name`, `package`, `service`, `category`, `command`, and `description`.
- Package detection through `dpkg-query` and `apt-cache`.
- Installed version display for detected packages.
- Command availability detection in the core checker.
- Systemd service state detection for configured services.
- Search and category filtering.
- Sequential install queue for selected packages.
- Log panel with automatic scrolling and status messages.

## Docker Development

Docker is intended for consistent lint/test/dev commands. GUI rendering inside the container requires extra X11 setup and is not expected to work by default.

The Compose service sets `QT_QPA_PLATFORM=offscreen` so Qt can initialize in Docker without a display server. This is useful for imports, tests, and smoke checks, but it will not show the GUI window.

Build and run tests:

```bash
docker compose build
docker compose run --rm fast-tools-dev
```

Run lint:

```bash
docker compose run --rm fast-tools-dev ruff check .
```

Run a Qt startup smoke check without showing a window:

```bash
docker compose run --rm fast-tools-dev python -m app.main --smoke-test
```

Do not use `python -m app.main` with the default Docker service unless you only want an invisible offscreen window. Qt may print `This plugin does not support propagateSizeHints()` when using the offscreen plugin; that message is harmless, but the app will not be visible.

Run the GUI inside the container only if you have configured display forwarding, and override the offscreen platform:

```bash
docker compose run --rm -e QT_QPA_PLATFORM=xcb -e DISPLAY=$DISPLAY fast-tools-dev python -m app.main
```

On Linux hosts, X11 forwarding usually also requires mounting the X11 socket and allowing local Docker clients to connect to your X server. This is intentionally not enabled by default because the app is meant to run locally on Ubuntu and Docker is mainly for tests and development commands.

## Project Structure

```text
fast-tools/
├── docker-compose.yml
├── Dockerfile
├── requirements.txt
├── README.md
├── app/
│   ├── main.py
│   ├── gui/
│   │   └── main_window.py
│   ├── core/
│   │   ├── package_checker.py
│   │   ├── installer.py
│   │   ├── service_manager.py
│   │   └── tools_config.py
│   └── config/
│       └── tools.json
└── tests/
    └── test_core.py
```
