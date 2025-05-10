"""
Manages application configuration by loading environment variables and providing default values.
Also includes utility for setting up colored logging and a dictionary of emojis for log messages.
"""
import os
from pathlib import Path
import logging
import colorlog

IN_DOCKER = os.path.exists('/.dockerenv')
if IN_DOCKER:
    DEFAULT_CONFIG_PATH = Path("/config/conf.yml")
else:
    DEFAULT_CONFIG_PATH = Path(__file__).resolve().parent.parent / "config" / "conf.yml"

DASHY_LOG_LEVEL = os.getenv("DASHY_LOG_LEVEL", "INFO").upper()
DASHY_CONFIG_PATH = Path(os.getenv("DASHY_CONFIG_PATH", DEFAULT_CONFIG_PATH))
DASHY_DOCKER_SECTION_NAME = os.getenv("DASHY_DOCKER_SECTION_NAME", "Docker Containers")
DASHY_RESET_ON_START = os.getenv("DASHY_RESET_ON_START", "true").lower() == "true"
DASHY_DOCKER_URL_HOST = os.getenv("DASHY_DOCKER_URL_HOST", "localhost")
DASHY_DOCKER_URL_TEMPLATE = os.getenv("DASHY_DOCKER_URL_TEMPLATE", "http://{host}:{port}")
DASHY_DOCKER_TITLE_TEMPLATE = os.getenv("DASHY_DOCKER_TITLE_TEMPLATE", "{name}")
DASHY_DOCKER_ICON_TEMPLATE = os.getenv("DASHY_DOCKER_ICON_TEMPLATE", "hl-{name}")
DASHY_DOCKER_LABEL_REGEX = os.getenv("DASHY_DOCKER_LABEL_REGEX", r"^(?:dashy$|dashy\..+)")
DASHY_DOCKER_PORT_LABEL_REGEX = os.getenv("DASHY_DOCKER_PORT_LABEL_REGEX", r"^dashy\.port$")
DASHY_DOCKER_IGNORE_LABEL_REGEX = os.getenv("DASHY_DOCKER_IGNORE_LABEL_REGEX", r"^dashy\.ignore$")
DASHY_EXPOSED_BY_DEFAULT = os.getenv("DASHY_EXPOSED_BY_DEFAULT", "false").lower() == "true"

EMOJIS = {
    'DEBUG': '🐛',
    'INFO': '✨',
    'START': '🚀',
    'SUCCESS': '✅',
    'FAILURE': '❌',
    'WARNING': '⚠️',
    'DOCKER': '🐳',
    'CONFIG': '⚙️',
    'SCAN': '🔍',
    'EVENT': '⚡️',
    'SAVE': '💾',
    'REMOVE': '🗑️',
    'ADD': '➕',
    'SKIP': '⏭️',
    'SHUTDOWN': '👋',
    'NETWORK': '🌐',
}

def setup_logging():
    """Configures logging with colorlog and a custom format."""
    log_level_app = getattr(logging, DASHY_LOG_LEVEL, logging.INFO)
    
    logger = logging.getLogger()
    logger.setLevel(log_level_app)

    if logger.hasHandlers():
        for handler in logger.handlers[:]:
            logger.removeHandler(handler)

    log_format = (
        "%(asctime)s "
        "%(log_color)s%(levelname)-8s%(reset)s "
        "%(message_log_color)s%(message)s"
    )
    
    formatter = colorlog.ColoredFormatter(
        log_format,
        datefmt='%Y-%m-%d %H:%M:%S',
        reset=True,
        log_colors={
            'DEBUG': 'cyan',
            'INFO': 'green',
            'WARNING': 'yellow',
            'ERROR': 'red',
            'CRITICAL': 'red,bg_white',
        },
        secondary_log_colors={
            'message': {
                'DEBUG': 'light_black',
                'INFO': 'blue', 
                'WARNING': 'yellow',
                'ERROR': 'red',
                'CRITICAL': 'bold_red',
            }
        },
        style='%'
    )

    handler = logging.StreamHandler()
    handler.setFormatter(formatter)
    logger.addHandler(handler)

    logging.info(f"{EMOJIS['START']} Logging initialized with style!")
