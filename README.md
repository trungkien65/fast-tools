# Fast Tools

Fast Tools is a Python / PySide6 desktop app for Ubuntu that checks common
developer packages and installs selected packages through `pkexec apt install -y`.

The GUI does not need to run as root. `pkexec` will ask for authorization only when installation is requested.

## Requirements

- Ubuntu or another Debian-based Linux distribution.
- Python 3.12 for the Docker image, or Python 3.11+ for local development.
- `apt`, `apt-cache`, and `dpkg-query` available on the host.
- `pkexec` for graphical privilege prompts. If `pkexec` is unavailable, installs fall back to `sudo`.

## Quick Start

Run locally on Ubuntu:

```bash
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m app.main
```

You can also use the root wrapper:

```bash
python main.py
```

Run tests:

```bash
python -m pytest
```

Run a Qt startup smoke check without opening the full window:

```bash
QT_QPA_PLATFORM=offscreen python -m app.main --smoke-test
```

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

Default groups include:

- Tools: build tooling such as `build-essential`, `cmake`, compilers, `jq`.
- Database: MySQL, PostgreSQL, SQLite, Redis, MongoDB client tools when available.
- IDE: VS Code, Vim, Neovim.
- Code: Git, Git LFS, Subversion.
- Office: LibreOffice, Thunderbird, GIMP, Flameshot.
- Network: curl, wget, SSH, DNS tools, net-tools, nmap, FileZilla.
- Web, runtime, container, and system tools for common developer workflows.

`code` requires the Microsoft apt repository. Without that repository, Fast Tools will show `Package not found`.

## Runtime Behavior

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
- Componentized PySide6 GUI with separate tool card, filter, grouped list, action, and log widgets.
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

## Release and Install via install.sh

Fast Tools supports script-based release, install, update, and uninstall without `.deb`.

### Build release artifacts

Prepare architecture binaries first:

- `artifacts/linux-amd64/fast-tools`
- `artifacts/linux-arm64/fast-tools`
- Optional icon: `artifacts/common/icon.png`

Generate release bundle:

```bash
./scripts/build-release.sh
```

Output:

```text
dist-release/
├── install.sh
├── uninstall.sh
├── fast-tools-linux-amd64-v<version>.tar.gz
├── fast-tools-linux-amd64-v<version>.tar.gz.sha256
├── fast-tools-linux-arm64-v<version>.tar.gz
└── fast-tools-linux-arm64-v<version>.tar.gz.sha256
```

### Publish

Push a version tag and let GitHub Actions build and upload release assets to GitHub Releases.

### User install / update / uninstall

Install:

```bash
curl -fsSL https://raw.githubusercontent.com/trungkien65/fast-tools/main/install.sh | bash
```

Check version:

```bash
fast-tools --version
```

Update:

```bash
fast-tools --update
```

Uninstall:

```bash
fast-tools --uninstall
```

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
│   │   ├── components.py
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
