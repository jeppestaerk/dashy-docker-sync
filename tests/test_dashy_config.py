import unittest
from unittest.mock import patch, mock_open, MagicMock, call
import yaml
import os
from pathlib import Path

from app import dashy_config
from app import app_config

class TestDashyConfig(unittest.TestCase):

    def setUp(self):
        import importlib
        self.patch_env = patch.dict(os.environ, {
            "DASHY_CONFIG_PATH": "/mock/config.yml",
            "DASHY_DOCKER_SECTION_NAME": "Test Docker Section",
            "DASHY_RESET_ON_START": "true",
            "DASHY_DOCKER_URL_HOST": "testhost",
            "DASHY_DOCKER_URL_TEMPLATE": "http://{host}:{port}/{name}",
            "DASHY_DOCKER_TITLE_TEMPLATE": "Title-{name}",
            "DASHY_DOCKER_ICON_TEMPLATE": "icon/{name}.png"
        }, clear=True)
        self.patch_env.start()
        
        importlib.reload(app_config)
        importlib.reload(dashy_config)
        
        dashy_config.DASHY_CONFIG_PATH = Path(app_config.DASHY_CONFIG_PATH)

    def tearDown(self):
        self.patch_env.stop()
        import importlib
        with patch.dict(os.environ, {}, clear=True):
             importlib.reload(app_config)
        importlib.reload(dashy_config)

    @patch('builtins.open', new_callable=mock_open)
    @patch('yaml.safe_load')
    @patch('pathlib.Path.exists')
    def test_load_initial_config_exists_valid(self, mock_exists, mock_yaml_load, mock_file_open):
        mock_exists.return_value = True
        mock_config_data = {
            "pageInfo": {"title": "My Dashy"},
            "appConfig": {"theme": "dark"},
            "sections": [{"name": "Test Docker Section", "items": []}]
        }
        mock_yaml_load.return_value = mock_config_data
        
        config = dashy_config.load_initial_config()
        
        mock_file_open.assert_called_once_with(dashy_config.DASHY_CONFIG_PATH, "r")
        mock_yaml_load.assert_called_once()
        self.assertEqual(config, mock_config_data)

    @patch('builtins.open', new_callable=mock_open)
    @patch('yaml.safe_load')
    @patch('pathlib.Path.exists')
    def test_load_initial_config_exists_empty_or_invalid_yaml(self, mock_exists, mock_yaml_load, mock_file_open):
        mock_exists.return_value = True
        mock_yaml_load.return_value = None
        
        config = dashy_config.load_initial_config()
        
        self.assertIn("sections", config)
        docker_section = next(s for s in config["sections"] if s["name"] == "Test Docker Section")
        self.assertIsNotNone(docker_section)
        self.assertEqual(docker_section["items"], [])

    @patch('pathlib.Path.exists')
    def test_load_initial_config_not_exists(self, mock_exists):
        mock_exists.return_value = False
        
        config = dashy_config.load_initial_config()
        
        self.assertIn("pageInfo", config)
        self.assertIn("appConfig", config)
        self.assertIn("sections", config)
        docker_section = next(s for s in config["sections"] if s["name"] == "Test Docker Section")
        self.assertIsNotNone(docker_section)
        self.assertEqual(docker_section["name"], "Test Docker Section")
        self.assertEqual(docker_section["items"], [])

    @patch('pathlib.Path.exists')
    @patch('builtins.open', new_callable=mock_open, read_data='sections:\n  - name: Other Section')
    @patch('yaml.safe_load', return_value={"sections": [{"name": "Other Section"}]})
    def test_load_initial_config_docker_section_missing(self, mock_yaml_load, mock_file_open, mock_exists):
        mock_exists.return_value = True
        config = dashy_config.load_initial_config()
        docker_section = next(s for s in config["sections"] if s["name"] == "Test Docker Section")
        self.assertIsNotNone(docker_section)
        self.assertEqual(len(config["sections"]), 2)

    def test_apply_startup_reset_true_items_exist(self):
        config = {"sections": [{"name": "Test Docker Section", "items": [{"title": "item1"}]}]}
        with patch.object(dashy_config, 'DASHY_RESET_ON_START', True):
            changed = dashy_config.apply_startup_reset(config)
            self.assertTrue(changed)
            self.assertEqual(config["sections"][0]["items"], [])

    def test_apply_startup_reset_true_items_empty(self):
        config = {"sections": [{"name": "Test Docker Section", "items": []}]}
        with patch.object(dashy_config, 'DASHY_RESET_ON_START', True):
            changed = dashy_config.apply_startup_reset(config)
            self.assertFalse(changed)
            self.assertEqual(config["sections"][0]["items"], [])
            
    def test_apply_startup_reset_true_section_missing(self):
        config = {"sections": [{"name": "Another Section", "items": [{"title": "item1"}]}]}
        with patch.object(dashy_config, 'DASHY_RESET_ON_START', True):
            changed = dashy_config.apply_startup_reset(config)
            self.assertFalse(changed)
            self.assertEqual(len(config["sections"][0]["items"]), 1)


    def test_apply_startup_reset_false(self):
        config = {"sections": [{"name": "Test Docker Section", "items": [{"title": "item1"}]}]}
        with patch.object(dashy_config, 'DASHY_RESET_ON_START', False):
            changed = dashy_config.apply_startup_reset(config)
            self.assertFalse(changed)
            self.assertEqual(len(config["sections"][0]["items"]), 1)

    @patch('builtins.open', new_callable=mock_open)
    @patch('yaml.dump')
    def test_save_config(self, mock_yaml_dump, mock_file_open):
        test_data = {"key": "value"}
        dashy_config.save_config(test_data)
        
        mock_file_open.assert_called_once_with(dashy_config.DASHY_CONFIG_PATH, "w")
        mock_yaml_dump.assert_called_once_with(test_data, mock_file_open(), sort_keys=False, default_flow_style=False)

    def test_generate_entry(self):
        container_info = {"name": "my-app", "port": "8080"}
        entry = dashy_config.generate_entry(container_info)
        self.assertEqual(entry["title"], "Title-my-app")
        self.assertEqual(entry["url"], "http://testhost:8080/my-app")
        self.assertEqual(entry["icon"], "icon/my-app.png")

    def test_generate_entry_no_name(self):
        container_info = {"port": "8080"}
        entry = dashy_config.generate_entry(container_info)
        self.assertIsNone(entry)

    @patch('app.dashy_config.save_config')
    def test_update_entry_new(self, mock_save_config):
        config = {"sections": [{"name": "Test Docker Section", "items": []}]}
        container_info = {"name": "app1", "port": "1111"}
        
        dashy_config.update_entry(config, container_info)
        
        section = config["sections"][0]
        self.assertEqual(len(section["items"]), 1)
        self.assertEqual(section["items"][0]["title"], "Title-app1")
        mock_save_config.assert_called_once_with(config)

    @patch('app.dashy_config.save_config')
    def test_update_entry_existing(self, mock_save_config):
        config = {"sections": [{"name": "Test Docker Section", "items": [
            {"title": "Title-app1", "url": "old_url"}
        ]}]}
        container_info = {"name": "app1", "port": "2222"}
        
        dashy_config.update_entry(config, container_info)
        
        section = config["sections"][0]
        self.assertEqual(len(section["items"]), 1)
        self.assertEqual(section["items"][0]["title"], "Title-app1")
        self.assertEqual(section["items"][0]["url"], "http://testhost:2222/app1")
        mock_save_config.assert_called_once_with(config)

    @patch('app.dashy_config.save_config')
    def test_update_entry_section_missing_creates_it(self, mock_save_config):
        config = {"sections": []}
        container_info = {"name": "app2", "port": "3333"}

        dashy_config.update_entry(config, container_info)

        self.assertEqual(len(config["sections"]), 1)
        section = config["sections"][0]
        self.assertEqual(section["name"], "Test Docker Section")
        self.assertEqual(len(section["items"]), 1)
        self.assertEqual(section["items"][0]["title"], "Title-app2")
        mock_save_config.assert_called_once_with(config)


    @patch('app.dashy_config.save_config')
    def test_remove_entry_existing(self, mock_save_config):
        config = {"sections": [{"name": "Test Docker Section", "items": [
            {"title": "Title-app1"}, {"title": "Title-app2"}
        ]}]}
        
        dashy_config.remove_entry(config, "app1")
        
        section = config["sections"][0]
        self.assertEqual(len(section["items"]), 1)
        self.assertEqual(section["items"][0]["title"], "Title-app2")
        mock_save_config.assert_called_once_with(config)

    @patch('app.dashy_config.save_config')
    def test_remove_entry_not_existing(self, mock_save_config):
        config = {"sections": [{"name": "Test Docker Section", "items": [
            {"title": "Title-app2"}
        ]}]}
        
        dashy_config.remove_entry(config, "app1")
        
        section = config["sections"][0]
        self.assertEqual(len(section["items"]), 1)
        mock_save_config.assert_not_called()

    @patch('app.dashy_config.save_config')
    def test_remove_entry_section_missing(self, mock_save_config):
        config = {"sections": []}
        
        dashy_config.remove_entry(config, "app1")
        
        self.assertEqual(len(config["sections"]), 0)
        mock_save_config.assert_not_called()


if __name__ == '__main__':
    unittest.main()
