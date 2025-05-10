"""
Handles Docker client interaction, container information extraction,
and filtering based on labels and configuration.
"""
import os
import re
import docker
from .app_config import (
    setup_logging,
    DASHY_DOCKER_LABEL_REGEX,
    DASHY_DOCKER_PORT_LABEL_REGEX,
    DASHY_EXPOSED_BY_DEFAULT,
    DASHY_DOCKER_IGNORE_LABEL_REGEX,
    EMOJIS
)
import logging


DOCKER_SOCKET = os.getenv("DOCKER_SOCKET", "unix://var/run/docker.sock")
DOCKER_LABEL_PATTERN = re.compile(DASHY_DOCKER_LABEL_REGEX, re.IGNORECASE)
DOCKER_PORT_LABEL_PATTERN = re.compile(DASHY_DOCKER_PORT_LABEL_REGEX, re.IGNORECASE)
DOCKER_IGNORE_LABEL_PATTERN = re.compile(DASHY_DOCKER_IGNORE_LABEL_REGEX, re.IGNORECASE)

def get_docker_client():
    """
    Initializes and returns a Docker client instance.

    Raises:
        docker.errors.DockerException: If the client fails to initialize or connect.

    Returns:
        docker.DockerClient: An initialized Docker client.
    """
    logging.debug(f"{EMOJIS['DOCKER']} Creating Docker client with socket: {DOCKER_SOCKET}...")
    try:
        client = docker.DockerClient(base_url=DOCKER_SOCKET)
    except docker.errors.DockerException as e:
        logging.error(f"{EMOJIS['FAILURE']} Failed to initialize Docker client with socket {DOCKER_SOCKET}: {e}")
        raise
    return client

def get_container_port(container):
    """
    Extracts the port for a given container.

    It first checks for a port specified by a label matching DOCKER_PORT_LABEL_PATTERN.
    If not found, it attempts to use the first exposed host port.

    Args:
        container: The Docker container object.

    Returns:
        str: The determined port number as a string, or None if no suitable port is found.
    """
    try:
        labels = container.labels
        port = next((v for k, v in labels.items() if DOCKER_PORT_LABEL_PATTERN.match(k)), None)
        if port:
            logging.debug(f"{EMOJIS['DEBUG']} Port {port} found from label for container {container.name}")
        else:
            logging.debug(f"{EMOJIS['DEBUG']} No specific Dashy port label found for {container.name}, checking exposed ports.")
            ports = container.ports or {}
            for port_mappings in ports.values():
                if port_mappings and isinstance(port_mappings, list):
                    for mapping in port_mappings:
                        if "HostPort" in mapping:
                            port = mapping["HostPort"]
                            logging.debug(f"{EMOJIS['DEBUG']} Port {port} found from exposed HostPort for container {container.name}")
                            break
                    if port:
                        break
            if not port:
                logging.debug(f"{EMOJIS['DEBUG']} No suitable port found for container {container.name} after checking labels and exposed ports.")

        logging.debug(f"{EMOJIS['DEBUG']} Final port extracted: {port} for container {container.name}")
        return port
    except Exception as e:
        logging.error(f"{EMOJIS['FAILURE']} Failed to extract port for {container.name}: {e}")
        return None

def get_container_info(container):
    """
    Extracts relevant information (name, port) from a container if it meets inclusion criteria.

    The criteria are:
    1. Not explicitly ignored by a label matching DASHY_DOCKER_IGNORE_LABEL_REGEX with value "true".
    2. If not ignored:
       a. Included if DASHY_EXPOSED_BY_DEFAULT is true.
       b. If DASHY_EXPOSED_BY_DEFAULT is false, included if the container has a label key
          matching DASHY_DOCKER_LABEL_REGEX AND the value of that label is NOT "false"
          (case-insensitive).

    Args:
        container: The Docker container object.

    Returns:
        dict: A dictionary containing 'name' and 'port' if the container should be included,
              otherwise None.
    """
    labels = container.labels
    logging.debug(f"{EMOJIS['DEBUG']} Trying to match labels for container {container.name} with pattern string from app_config: {DASHY_DOCKER_LABEL_REGEX}")
    logging.debug(f"{EMOJIS['DEBUG']} Compiled DOCKER_LABEL_PATTERN is using pattern string: '{DOCKER_LABEL_PATTERN.pattern}' with flags {DOCKER_LABEL_PATTERN.flags}")
    logging.debug(f"{EMOJIS['DEBUG']} Compiled DOCKER_IGNORE_LABEL_PATTERN is using pattern string: '{DOCKER_IGNORE_LABEL_PATTERN.pattern}' with flags {DOCKER_IGNORE_LABEL_PATTERN.flags}")
    logging.debug(f"{EMOJIS['SCAN']} Inspecting container: {container.name}, labels: {labels}")

    # 1. Check for ignore label first
    for k_ignore, v_ignore in labels.items(): # Iterate over items (key, value)
        if DOCKER_IGNORE_LABEL_PATTERN.match(k_ignore):
            logging.debug(f"{EMOJIS['DEBUG']} Found potential ignore label key '{k_ignore}' with value '{v_ignore}'.")
            if isinstance(v_ignore, str) and v_ignore.lower() == "true":
                logging.debug(f"{EMOJIS['SKIP']} Container {container.name} ignored because label key '{k_ignore}' matched DASHY_DOCKER_IGNORE_LABEL_REGEX and its value is 'true'.")
                return None # Ignore the container
            else:
                # If a label matches the ignore pattern but its value is not "true",
                # it does not cause an ignore. The loop continues to check other labels,
                # in case another label matches the ignore pattern with a "true" value.
                logging.debug(f"{EMOJIS['DEBUG']} Ignore label key '{k_ignore}' matched, but value is not 'true' (it's '{v_ignore}'). Not ignoring based on this specific label.")
    
    # 2. If not ignored by a "true" ignore label, proceed with inclusion logic
    include_container = False
    if DASHY_EXPOSED_BY_DEFAULT:
        include_container = True
        logging.debug(f"{EMOJIS['DEBUG']} Container {container.name} considered for inclusion because DASHY_EXPOSED_BY_DEFAULT is true.")
    else:
        for k_include, v_include in labels.items():
            if DOCKER_LABEL_PATTERN.match(k_include):
                logging.debug(f"{EMOJIS['DEBUG']} Found potential inclusion label key '{k_include}' with value '{v_include}'.")
                if isinstance(v_include, str) and v_include.lower() == "false":
                    logging.debug(f"{EMOJIS['DEBUG']} Inclusion label key '{k_include}' has value 'false'. Not including based on this label. Checking other labels.")
                    # This label explicitly says "false", so it doesn't grant inclusion.
                    # Continue to check if other labels might grant inclusion.
                else:
                    # Label key matches and value is not "false" (e.g., "true", any other string, or no value)
                    include_container = True
                    logging.debug(f"{EMOJIS['DEBUG']} Container {container.name} considered for inclusion because label key '{k_include}' matched DASHY_DOCKER_LABEL_REGEX and value is not 'false'.")
                    break # Found a valid inclusion label
    
    if not include_container:
        logging.debug(f"{EMOJIS['SKIP']} Container {container.name} skipped (not exposed by default and no matching include label, or was explicitly ignored).")
        return None

    try:
        container_info = {
            "name": container.name,
            "port": get_container_port(container)
        }
        logging.info(f"{EMOJIS['SUCCESS']} Including container: {container.name}")
        logging.debug(f"{EMOJIS['DEBUG']} Container info extracted: {container_info}")
        return container_info
    except Exception as e:
        logging.error(f"{EMOJIS['FAILURE']} Failed to extract container info for {container.name}: {e}")
        return None
