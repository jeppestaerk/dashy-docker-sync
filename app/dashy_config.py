"""
Manages loading, modifying, and saving the Dashy YAML configuration file.
Includes logic for adding, updating, and removing container entries in a designated section.
"""
import yaml
from pathlib import Path
from .app_config import (
    setup_logging,
    DASHY_CONFIG_PATH,
    DASHY_RESET_ON_START,
    DASHY_DOCKER_SECTION_NAME,
    DASHY_DOCKER_URL_HOST,
    DASHY_DOCKER_TITLE_TEMPLATE,
    DASHY_DOCKER_URL_TEMPLATE,
    DASHY_DOCKER_ICON_TEMPLATE,
    EMOJIS
)
import logging

def load_initial_config():
    """
    Loads the Dashy configuration from the path specified by DASHY_CONFIG_PATH.
    If the file doesn't exist or is invalid, it initializes a default configuration structure.
    Ensures the target Docker section exists.

    Returns:
        dict: The loaded or initialized Dashy configuration.
    """
    if DASHY_CONFIG_PATH.exists():
        logging.info(f"{EMOJIS['CONFIG']} Loading config from {DASHY_CONFIG_PATH}")
        try:
            with open(DASHY_CONFIG_PATH, "r") as f:
                config = yaml.safe_load(f) or {}
        except IOError as e:
            logging.error(f"{EMOJIS['FAILURE']} Error reading config file {DASHY_CONFIG_PATH}: {e}")
            config = {
                "pageInfo": {
                    "title": "Home Lab",
                    "navLinks": [
                        {"title": "GitHub", "path": "https://github.com/Lissy93/dashy"},
                        {"title": "Documentation", "path": "https://dashy.to/docs"}
                    ]
                },
                "appConfig": {
                    "theme": "nord-frost"
                },
                "sections": []
            }
    else:
        logging.info(f"{EMOJIS['CONFIG']} Config file not found at {DASHY_CONFIG_PATH}, initializing new config")
        config = {
            "pageInfo": {
                "title": "Home Lab",
                "navLinks": [
                    {"title": "GitHub", "path": "https://github.com/Lissy93/dashy"},
                    {"title": "Documentation", "path": "https://dashy.to/docs"}
                ]
            },
            "appConfig": {
                "theme": "nord-frost"
            },
            "sections": []
        }

    if "sections" not in config or not isinstance(config["sections"], list):
        logging.debug(f"{EMOJIS['CONFIG']} Initializing 'sections' as an empty list in config")
        config["sections"] = []

    existing_section = next((s for s in config["sections"] if s.get("name") == DASHY_DOCKER_SECTION_NAME), None)
    if not existing_section:
        logging.info(f"{EMOJIS['ADD']} Creating new section in config: {DASHY_DOCKER_SECTION_NAME}")
        config["sections"].append({
            "name": DASHY_DOCKER_SECTION_NAME,
            "icon": "https://cdn.jsdelivr.net/gh/homarr-labs/dashboard-icons/svg/docker.svg",
            "displayData": {
                "color": "#1D63ED",
            },
            "items": []
        })
    return config

def apply_startup_reset(config):
    """Applies the DASHY_RESET_ON_START logic to the loaded config."""
    if DASHY_RESET_ON_START:
        docker_section = next((s for s in config.get("sections", []) if s.get("name") == DASHY_DOCKER_SECTION_NAME), None)
        if docker_section:
            if "items" not in docker_section or not isinstance(docker_section.get("items"), list) or docker_section.get("items"):
                logging.info(f"{EMOJIS['CONFIG']} Resetting section items for: {DASHY_DOCKER_SECTION_NAME} due to DASHY_RESET_ON_START")
                docker_section["items"] = []
                return True
            else:
                logging.debug(f"{EMOJIS['DEBUG']} Section items for {DASHY_DOCKER_SECTION_NAME} already empty or 'items' key missing/invalid; no reset needed.")
                return False
        else:
            logging.debug(f"{EMOJIS['DEBUG']} Docker section {DASHY_DOCKER_SECTION_NAME} not found; no reset applied.")
            return False
    else:
        logging.debug(f"{EMOJIS['DEBUG']} DASHY_RESET_ON_START is false; no reset applied.")
    return False

def save_config(data):
    """
    Saves the given Dashy configuration data to the YAML file.

    Args:
        data (dict): The Dashy configuration dictionary to save.
    """
    try:
        logging.info(f"{EMOJIS['SAVE']} Saving updated config to {DASHY_CONFIG_PATH}")
        with open(DASHY_CONFIG_PATH, "w") as f:
            yaml.dump(data, f, sort_keys=False, default_flow_style=False)
    except (IOError, yaml.YAMLError) as e:
        logging.error(f"{EMOJIS['FAILURE']} Failed to save config to {DASHY_CONFIG_PATH}: {e}")
    except Exception as e:
        logging.error(f"{EMOJIS['FAILURE']} An unexpected error occurred while saving config: {e}")

def generate_entry(container_info: dict):
    """
    Generates a Dashy item entry dictionary based on container information and templates.

    Args:
        container_info (dict): A dictionary containing 'name' and 'port' of the container.

    Returns:
        dict: A Dashy item entry, or None if 'name' is missing in container_info.
    """
    if not container_info.get("name"):
        logging.warning(f"{EMOJIS['WARNING']} Skipping container entry generation: 'name' is missing.")
        return None
    host = DASHY_DOCKER_URL_HOST
    name = container_info.get("name", "")
    port = container_info.get("port", "")
    return {
        "title": DASHY_DOCKER_TITLE_TEMPLATE.format(name=name),
        "url": DASHY_DOCKER_URL_TEMPLATE.format(host=host, port=port, name=name),
        "icon": DASHY_DOCKER_ICON_TEMPLATE.format(name=name),
    }

def update_entry(config: dict, container_info: dict):
    """
    Adds or updates an entry for a container in the Dashy configuration.

    If an entry with the same title (generated from container_info['name']) exists,
    it's replaced. Otherwise, a new entry is added. Entries are sorted by title.

    Args:
        config (dict): The current Dashy configuration.
        container_info (dict): Information about the container to add/update.
    """
    if not container_info or not container_info.get("name"):
        logging.warning(f"{EMOJIS['WARNING']} Skipping update: invalid container_info.")
        return

    logging.info(f"{EMOJIS['ADD']} Updating entry for container: {container_info['name']}")

    sections = config.get("sections", [])
    docker_section = next((s for s in sections if s.get("name") == DASHY_DOCKER_SECTION_NAME), None)

    if not docker_section:
        logging.error(f"{EMOJIS['FAILURE']} Docker section '{DASHY_DOCKER_SECTION_NAME}' not found. This should not happen. Creating it.")
        docker_section = {
            "name": DASHY_DOCKER_SECTION_NAME,
            "icon": "https://cdn.jsdelivr.net/gh/homarr-labs/dashboard-icons/svg/docker.svg",
            "displayData": {"color": "#1D63ED"},
            "items": []
        }
        sections.append(docker_section)
        config["sections"] = sections

    items = docker_section.get("items") or []
    
    expected_title = DASHY_DOCKER_TITLE_TEMPLATE.format(name=container_info["name"])
    items = [e for e in items if isinstance(e, dict) and e.get("title") != expected_title]
    
    new_entry = generate_entry(container_info)
    if new_entry:
        logging.info(f"{EMOJIS['ADD']} Appending new entry: {new_entry['title']}")
        items.append(new_entry)
        items.sort(key=lambda e: e.get("title", "").lower())
        docker_section["items"] = items
    else:
        logging.warning(f"{EMOJIS['WARNING']} Failed to generate entry for {container_info['name']}, not adding.")

    save_config(config)

def remove_entry(config: dict, container_name: str):
    """
    Removes an entry for a container from the Dashy configuration.

    The entry is identified by its title, which is generated from the container_name
    using DASHY_DOCKER_TITLE_TEMPLATE.

    Args:
        config (dict): The current Dashy configuration.
        container_name (str): The name of the container whose entry should be removed.
    """
    logging.info(f"{EMOJIS['REMOVE']} Attempting to remove entry for container: {container_name}")

    sections = config.get("sections", [])
    docker_section = next((s for s in sections if s.get("name") == DASHY_DOCKER_SECTION_NAME), None)

    if docker_section:
        items = docker_section.get("items", [])
        expected_title = DASHY_DOCKER_TITLE_TEMPLATE.format(name=container_name)
        original_item_count = len(items)
        new_items = [e for e in items if not (isinstance(e, dict) and e.get("title") == expected_title)]
        
        if len(new_items) < original_item_count:
            logging.info(f"{EMOJIS['SUCCESS']} Entry found and removed for: {container_name}")
            docker_section["items"] = new_items
            save_config(config)
        else:
            logging.info(f"{EMOJIS['INFO']} No matching entry found for title: {expected_title} during remove.")
    else:
        logging.warning(f"{EMOJIS['WARNING']} Docker section '{DASHY_DOCKER_SECTION_NAME}' not found during remove operation for {container_name}.")