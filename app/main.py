"""
Main application entry point.
Initializes Docker client, loads Dashy configuration, performs an initial scan of running containers,
and then listens for Docker events to dynamically update the Dashy configuration.
Handles graceful shutdown and retries on connection errors.
"""
from .docker_utils import get_docker_client, get_container_info
from .dashy_config import (
    load_initial_config,
    apply_startup_reset,
    save_config,
    update_entry,
    remove_entry
)
import docker
from .app_config import (
    setup_logging,
    EMOJIS
)
import requests
import time
import logging

setup_logging()

logging.info(f"{EMOJIS['DOCKER']} Initializing Docker client...")
try:
    client = get_docker_client()
    client.ping()
    logging.info(f"{EMOJIS['SUCCESS']} Docker client initialized and connected.")
except docker.errors.DockerException as e:
    logging.error(f"{EMOJIS['FAILURE']} Failed to connect to Docker: {e}")
    exit(1) 

logging.info(f"{EMOJIS['CONFIG']} Loading and initializing Dashy config...")
current_config = load_initial_config()
if apply_startup_reset(current_config):
    save_config(current_config)

logging.info(f"{EMOJIS['SCAN']} Scanning existing containers on startup...")
for container in client.containers.list():
    logging.debug(f"{EMOJIS['DOCKER']} Found container: {container.name}")
    info = get_container_info(container)
    if info:
        logging.info(f"{EMOJIS['ADD']} Adding existing container on startup: {info['name']}")
        update_entry(current_config, info)
    else:
        logging.debug(f"{EMOJIS['SKIP']} Container {container.name} does not meet exposure criteria for startup scan")

logging.info(f"{EMOJIS['EVENT']} Listening for Docker events...")

while True:
    try:
        event_stream = client.events(decode=True)
        for event in event_stream:
            if event["Type"] == "container":
                action = event["Action"]
                container_id = event["id"]
                logging.debug(f"{EMOJIS['EVENT']} Received event: {action} for container ID: {container_id}")
                try:
                    container = client.containers.get(container_id)
                except docker.errors.NotFound:
                    logging.warning(f"{EMOJIS['WARNING']} Container not found for ID: {container_id}")
                    continue

                if action == "start":
                    info = get_container_info(container)
                    if info:
                        logging.info(f"{EMOJIS['ADD']} Updating entry for started container: {info['name']}")
                        update_entry(current_config, info)
                    else:
                        logging.debug(f"{EMOJIS['SKIP']} Started container {container.name} does not meet exposure criteria")

                elif action in ("die", "stop"):
                    logging.info(f"{EMOJIS['REMOVE']} Removing entry for stopped/died container: {container.name}")
                    remove_entry(current_config, container.name)
            else:
                logging.debug(f"{EMOJIS['EVENT']} Received non-container event: Type={event.get('Type')}, Action={event.get('Action')}")
    
    except KeyboardInterrupt:
        logging.info(f"\n{EMOJIS['SHUTDOWN']} Gracefully shutting down Dashy Docker Sync... Bye!\n")
        break
    except requests.exceptions.ReadTimeout:
        logging.warning(f"{EMOJIS['NETWORK']} Docker event stream timed out. Reconnecting...")
        time.sleep(5)
    except docker.errors.APIError as e:
        logging.error(f"{EMOJIS['FAILURE']} Docker API error in event stream: {e}. Reconnecting...")
        time.sleep(5)
    except Exception as e:
        logging.error(f"{EMOJIS['FAILURE']} Unexpected error in event stream: {e}. Attempting to reconnect...")
        time.sleep(10)