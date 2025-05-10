# Dashy Docker Sync

Dynamically update your [Dashy](https://dashy.to/) dashboard configuration based on Docker container lifecycle events. This tool listens to Docker events and automatically adds or removes services from a specified section in your Dashy `conf.yml`.

## ✨ Features

-   **Automatic Discovery:** Adds and removes services in Dashy as Docker containers start and stop.
-   **Label-Driven:** Highly configurable behavior based on Docker container labels.
    -   Expose containers explicitly via labels.
    -   Optionally expose all containers by default.
    -   Override detected ports using a specific label.
-   **Customizable Templates:** Define custom URL, title, and icon paths for your Dashy items using templates.
-   **Startup Reset:** Optionally clear the managed Dashy section on startup for a clean slate.
-   **Flexible Configuration:** All settings are manageable via environment variables.
-   **Lightweight:** Minimal dependencies and designed to run efficiently.

## 🤔 How It Works

The Dashy Docker Sync performs the following:

1.  **Connects to Docker:** Monitors Docker engine events (container start, stop, die).
2.  **Initial Scan:** On startup, it scans all currently running containers and updates Dashy accordingly.
3.  **Event Listening:**
    *   When a container **starts**, the updater checks if it should be added to Dashy based on your configuration (labels or `DASHY_EXPOSED_BY_DEFAULT`). If so, it generates an item and adds/updates it in the Dashy config.
    *   When a container **stops** or **dies**, the updater removes its corresponding item from the Dashy config.
4.  **Label Processing:**
    *   Containers are included if `DASHY_EXPOSED_BY_DEFAULT` is `true`, OR if they have a label key matching the `DASHY_DOCKER_LABEL_REGEX`.
    *   The port for the service URL can be explicitly set using a label key matching `DASHY_DOCKER_PORT_LABEL_REGEX`. If not found, it attempts to use the first mapped host port.
5.  **Configuration Update:** Changes are saved directly to your Dashy YAML configuration file.

## 🚀 Getting Started

### Prerequisites

-   Docker installed and running.
-   Your Dashy `conf.yml` file accessible to the updater.

### Option 1: Using Docker (Recommended)

This is the easiest way to run the Dashy Docker Sync.

```bash
docker run -d \
  --name dashy-docker-sync \
  --restart unless-stopped \
  -v /var/run/docker.sock:/var/run/docker.sock:ro \
  -v /path/to/your/dashy/conf.yml:/config/dashy-config.yml \
  \
  # --- Other Configuration Examples (see full list below) ---
  # -e DASHY_DOCKER_LABEL_REGEX="^dashy.include$" # Only include containers with 'dashy.include=true'
  # -e DASHY_EXPOSED_BY_DEFAULT="true" # Include all containers by default
  # -e DASHY_DOCKER_URL_HOST="your.domain.com" # If Dashy is accessed via a domain
  \
  ghcr.io/jeppestaerk/dashy-docker-sync:latest
```

**Note:**
*   Mount the Docker socket (`/var/run/docker.sock`) as read-only (`:ro`) if you prefer, as the application only needs to read events and container info.
    *   **Permissions for Docker Socket**: The user on the host system whose `UID` and `GID` are used by this container must have permissions to access `/var/run/docker.sock`. Typically, this means the host user should be a member of the `docker` group. You can add the current user to the `docker` group on the host with `sudo usermod -aG docker $USER` (a logout/login or reboot may be required for this change to take effect).
    *   **TLS-Enabled Docker Daemon**: TLS configuration has been removed for simplicity in the current default setup. If your Docker daemon requires TLS, you would need to adapt the Docker client connection (e.g., by using environment variables like `DOCKER_HOST`, `DOCKER_TLS_VERIFY`, `DOCKER_CERT_PATH` and modifying `app/docker_utils.py` to use `docker.from_env()`).
*   Adjust the volume path for your Dashy `conf.yml`.
*   The container now runs its process as root. UID/GID environment variables for the container process itself are no longer used by this image's default configuration.

### Option 2: Local Python Environment

For development or if you prefer not to use Docker for this tool:

1.  **Clone the repository (if you haven't already):**
    ```bash
    git clone https://github.com/jeppestaerk/dashy-docker-sync.git
    cd dashy-docker-sync
    ```

2.  **Set up a Python virtual environment (recommended):**
    ```bash
    python -m venv .venv
    source .venv/bin/activate  # On Windows: .venv\Scripts\activate
    ```

3.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Set environment variables (see "Configuration" section below).**
    For example, in your shell:
    ```bash
    export DASHY_CONFIG_PATH="./config/dashy-config.yml" # Adjust path
    # ... other variables
    ```

5.  **Run the application:**
    ```bash
    python -m app.main
    ```
    *(Note: When running locally, the application runs as your current system user.)*

## ⚠️ Important: File Permissions for `conf.yml`

When you mount your Dashy `conf.yml` file (e.g., `-v /path/to/your/dashy/conf.yml:/config/dashy-config.yml`), the application inside the container (now running as root) will have root's permissions to read/write this file. Files created or modified by the container in the mounted volume will be owned by root on the host system.

If you need the `conf.yml` (and any backups or other files it might create) to have specific ownership on the host, you may need to manage permissions on the host side or consider re-introducing a non-root user in the container for future enhancements.

## ⚙️ Configuration (Environment Variables)

The application is configured entirely through environment variables.

| Variable                        | Description                                                                                                | Default Value                      |
| ------------------------------- | ---------------------------------------------------------------------------------------------------------- | ---------------------------------- |
| `DASHY_CONFIG_PATH`             | Full path *inside the container* to your Dashy `conf.yml` file.                                            | `/config/dashy-config.yml`         |
| `DASHY_LOG_LEVEL`               | Logging verbosity (e.g., `DEBUG`, `INFO`, `WARNING`, `ERROR`).                                             | `INFO`                             |
| `DASHY_RESET_ON_START`          | If `true`, the specified Docker section in Dashy will be cleared of items on application startup.          | `true`                             |
| `DASHY_DOCKER_SECTION_NAME`     | The name of the section in your Dashy config where Docker container items will be managed.                 | `Docker Containers`                |
| `DASHY_EXPOSED_BY_DEFAULT`      | If `true`, all running containers will be considered for Dashy unless explicitly excluded by other logic. If `false`, only containers with a matching `DASHY_DOCKER_LABEL_REGEX` label will be considered. | `false`                            |
| `DASHY_DOCKER_LABEL_REGEX`      | A regex pattern to match against container label keys. If `DASHY_EXPOSED_BY_DEFAULT` is `false`, a container must have at least one label key matching this regex to be included. | `^(?:dashy$|dashy\..+)`          |
| `DASHY_DOCKER_IGNORE_LABEL_REGEX` | A regex pattern to match against container label keys. If any label key matches this regex AND its value is explicitly `"true"` (case-insensitive), the container will be skipped, regardless of other settings. If the value is `"false"` or anything else, this specific ignore label is ignored. | `^dashy\.ignore$`                    |
| `DASHY_DOCKER_PORT_LABEL_REGEX` | A regex pattern to match against container label keys for specifying the port. The value of this label will be used as the port. | `^dashy\.port$`                    |
| `DASHY_DOCKER_URL_HOST`         | The hostname or IP to use in the `{host}` placeholder of the `DASHY_DOCKER_URL_TEMPLATE`.                   | `localhost`                        |
| `DASHY_DOCKER_URL_TEMPLATE`     | Template for generating the item URL. Placeholders: `{host}`, `{port}`, `{name}` (container name).         | `http://{host}:{port}`             |
| `DASHY_DOCKER_TITLE_TEMPLATE`   | Template for generating the item title. Placeholder: `{name}` (container name).                            | `{name}`                           |
| `DASHY_DOCKER_ICON_TEMPLATE`    | Template for generating the item icon URL/path. Placeholder: `{name}`. Can point to local Dashy icons (e.g., `png/{name}.png`) or external URLs. | `hl-{name}`                   |
| `DOCKER_SOCKET`                 | Path to the Docker socket.                                                                                 | `unix://var/run/docker.sock`       |

## 💡 Usage Example

### 1. Target Container Labels

Let's say you have a container you want to appear in Dashy. You might run it with labels like this:

```bash
docker run -d \
  --name my-web-app \
  -p 8080:80 \
  --label dashy="include" \
  --label dashy.port="8080" \
  # --label dashy.icon="hl:/my-web-app.png" # Optional: custom icon
  # --label dashy.title="My Awesome Web App" # Optional: custom title (though template is usually better)
  ghcr.io/jeppestaerk/dashy-docker-sync:latest
```

**Explanation of labels based on default regexes:**
*   `dashy="include"`: This label key `dashy` matches the default `DASHY_DOCKER_LABEL_REGEX` (`^(?:dashy$|dashy\..+)`), so the container will be processed (assuming `DASHY_EXPOSED_BY_DEFAULT` is `false`). The value `"include"` is not strictly used by the default logic but makes the label's purpose clear.
*   `dashy.port="8080"`: This label key `dashy.port` matches `DASHY_DOCKER_PORT_LABEL_REGEX` (`^dashy\.port$`). Its value `8080` will be used as the `{port}` in the URL template.

### 2. Dashy Docker Sync Configuration

Assume the Dashy Docker Sync is running with `DASHY_DOCKER_URL_HOST` set to `my.homelab.lan` if you access services that way.

### 3. Resulting Dashy Configuration

The updater would add/update a section in your Dashy `conf.yml` similar to this:

```yaml
# ... other Dashy config ...

sections:
  - name: Docker Containers # Or your DASHY_DOCKER_SECTION_NAME
    icon: https://cdn.jsdelivr.net/gh/homarr-labs/dashboard-icons/svg/docker.svg
    displayData:
      color: "#1D63ED"
    items:
      - title: my-web-app # From DASHY_DOCKER_TITLE_TEMPLATE ({name})
        url: http://my.homelab.lan:8080 # From DASHY_DOCKER_URL_TEMPLATE
        icon: hl-my-web-app # From DASHY_DOCKER_ICON_TEMPLATE (default: hl-{name})

# ... other Dashy sections ...
```

## 📁 Project Layout

```
dashy-docker-sync/
├── app/
│   ├── main.py           # Main application script, event listener
│   ├── dashy_config.py   # Handles loading/saving Dashy YAML config
│   ├── docker_utils.py   # Docker client and container info extraction
│   └── app_config.py     # Manages environment variables and defaults
├── docker/
│   └── entrypoint.sh     # Script to handle UID/GID and start the app
├── config/
│   └── dashy-config.yml  # Example/default Dashy config (if used locally)
├── requirements.txt      # Python dependencies
├── Dockerfile            # For building the Docker image
└── README.md             # This file
```

## 🛠️ Development

(See "Local Python Environment" under Getting Started)

-   Consider using a tool like `pre-commit` for code formatting and linting.
-   Add unit tests for new functionality.

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request or open an Issue.

## 📄 License

This project is licensed under the MIT License - see the `LICENSE` file for details.
