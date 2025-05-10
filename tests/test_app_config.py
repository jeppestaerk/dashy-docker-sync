import unittest
import os
import logging
from unittest.mock import patch, MagicMock
from pathlib import Path
from app import app_config

class TestAppConfig(unittest.TestCase):

    @patch.dict(os.environ, {}, clear=True)
    @patch('app.app_config.IN_DOCKER', False)
    def test_default_values(self):
        import importlib
        importlib.reload(app_config)

        self.assertEqual(app_config.DASHY_LOG_LEVEL, "INFO")
        
        if app_config.IN_DOCKER:
            self.assertEqual(app_config.DASHY_CONFIG_PATH, Path("/config/conf.yml"))
        else:
            expected_path = Path(__file__).resolve().parent.parent / "config" / "conf.yml"
            self.assertEqual(app_config.DASHY_CONFIG_PATH, expected_path)
        
        self.assertEqual(app_config.DASHY_DOCKER_SECTION_NAME, "Docker Containers")
        self.assertTrue(app_config.DASHY_RESET_ON_START)
        self.assertEqual(app_config.DASHY_DOCKER_URL_HOST, "localhost")
        self.assertEqual(app_config.DASHY_DOCKER_URL_TEMPLATE, "http://{host}:{port}")
        self.assertEqual(app_config.DASHY_DOCKER_TITLE_TEMPLATE, "{name}")
        self.assertEqual(app_config.DASHY_DOCKER_ICON_TEMPLATE, "hl-{name}")
        self.assertEqual(app_config.DASHY_DOCKER_LABEL_REGEX, r"^(?:dashy$|dashy\..+)")
        self.assertEqual(app_config.DASHY_DOCKER_PORT_LABEL_REGEX, r"^dashy\.port$")
        self.assertEqual(app_config.DASHY_DOCKER_IGNORE_LABEL_REGEX, r"^dashy\.ignore$")
        self.assertFalse(app_config.DASHY_EXPOSED_BY_DEFAULT)

    @patch.dict(os.environ, {
        "DASHY_LOG_LEVEL": "DEBUG",
        "DASHY_CONFIG_PATH": "/test/config.yml",
        "DASHY_DOCKER_SECTION_NAME": "My Docker Services",
        "DASHY_RESET_ON_START": "false",
        "DASHY_DOCKER_URL_HOST": "example.com",
        "DASHY_DOCKER_URL_TEMPLATE": "https://{host}/{name}:{port}",
        "DASHY_DOCKER_TITLE_TEMPLATE": "Service: {name}",
        "DASHY_DOCKER_ICON_TEMPLATE": "ico/{name}.ico",
        "DASHY_DOCKER_LABEL_REGEX": r"^custom\.label$",
        "DASHY_DOCKER_PORT_LABEL_REGEX": r"^custom\.port$",
        "DASHY_DOCKER_IGNORE_LABEL_REGEX": r"^custom\.ignore$",
        "DASHY_EXPOSED_BY_DEFAULT": "true",
    }, clear=True)
    def test_env_overrides(self):
        import importlib
        importlib.reload(app_config)

        self.assertEqual(app_config.DASHY_LOG_LEVEL, "DEBUG")
        self.assertEqual(str(app_config.DASHY_CONFIG_PATH), "/test/config.yml")
        self.assertEqual(app_config.DASHY_DOCKER_SECTION_NAME, "My Docker Services")
        self.assertFalse(app_config.DASHY_RESET_ON_START)
        self.assertEqual(app_config.DASHY_DOCKER_URL_HOST, "example.com")
        self.assertEqual(app_config.DASHY_DOCKER_URL_TEMPLATE, "https://{host}/{name}:{port}")
        self.assertEqual(app_config.DASHY_DOCKER_TITLE_TEMPLATE, "Service: {name}")
        self.assertEqual(app_config.DASHY_DOCKER_ICON_TEMPLATE, "ico/{name}.ico")
        self.assertEqual(app_config.DASHY_DOCKER_LABEL_REGEX, r"^custom\.label$")
        self.assertEqual(app_config.DASHY_DOCKER_PORT_LABEL_REGEX, r"^custom\.port$")
        self.assertEqual(app_config.DASHY_DOCKER_IGNORE_LABEL_REGEX, r"^custom\.ignore$")
        self.assertTrue(app_config.DASHY_EXPOSED_BY_DEFAULT)

    def test_setup_logging(self):
        with patch.dict(os.environ, {"DASHY_LOG_LEVEL": "CRITICAL"}, clear=True):
            import importlib
            importlib.reload(app_config)

            app_config.setup_logging()
            
            logger = logging.getLogger()
            self.assertEqual(logger.level, logging.CRITICAL)
            self.assertTrue(any(isinstance(h, logging.StreamHandler) for h in logger.handlers))
            
            self.assertTrue(any(h.__class__.__name__ in ['StreamHandler', 'ColorizingStreamHandler', 'ColoredFormatter'] for h in logger.handlers for f in [h.formatter] if f))

    @classmethod
    def tearDownClass(cls):
        import importlib
        with patch.dict(os.environ, {}, clear=True):
            importlib.reload(app_config)


if __name__ == '__main__':
    unittest.main()
