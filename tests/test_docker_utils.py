import unittest
from unittest.mock import patch, MagicMock, PropertyMock
import re
import os

from app import docker_utils
from app import app_config

class TestDockerUtils(unittest.TestCase):

    def setUp(self):
        import importlib
        with patch.dict(os.environ, {}, clear=True):
            importlib.reload(app_config)
        importlib.reload(docker_utils)

    def tearDown(self):
        import importlib
        with patch.dict(os.environ, {}, clear=True):
            importlib.reload(app_config)
        importlib.reload(docker_utils)

    @patch('docker.DockerClient')
    def test_get_docker_client(self, mock_docker_client_constructor):
        mock_client_instance = MagicMock()
        mock_docker_client_constructor.return_value = mock_client_instance
        
        client = docker_utils.get_docker_client()
        
        mock_docker_client_constructor.assert_called_once_with(base_url=docker_utils.DOCKER_SOCKET)
        self.assertEqual(client, mock_client_instance)

    def _create_mock_container(self, name="test_container", labels=None, ports=None):
        container = MagicMock()
        container.name = name
        container.labels = labels if labels is not None else {}
        container.ports = ports if ports is not None else {}
        return container

    def test_get_container_port_from_label(self):
        docker_utils.DOCKER_PORT_LABEL_PATTERN = re.compile(app_config.DASHY_DOCKER_PORT_LABEL_REGEX)
        
        container = self._create_mock_container(labels={"dashy.port": "8080"})
        self.assertEqual(docker_utils.get_container_port(container), "8080")

        container_custom_label = self._create_mock_container(labels={"my.custom.port.label": "9090"})
        with patch.dict(os.environ, {"DASHY_DOCKER_PORT_LABEL_REGEX": r"^my\.custom\.port\.label$"}):
            import importlib
            importlib.reload(app_config)
            importlib.reload(docker_utils)
            self.assertEqual(docker_utils.get_container_port(container_custom_label), "9090")

    def test_get_container_port_from_exposed_host_port(self):
        container = self._create_mock_container(ports={"80/tcp": [{"HostIp": "0.0.0.0", "HostPort": "8081"}]})
        self.assertEqual(docker_utils.get_container_port(container), "8081")

    def test_get_container_port_no_label_no_exposed_port(self):
        container = self._create_mock_container()
        self.assertIsNone(docker_utils.get_container_port(container))

    def test_get_container_port_label_takes_precedence(self):
        docker_utils.DOCKER_PORT_LABEL_PATTERN = re.compile(app_config.DASHY_DOCKER_PORT_LABEL_REGEX)
        container = self._create_mock_container(
            labels={"dashy.port": "1234"},
            ports={"80/tcp": [{"HostIp": "0.0.0.0", "HostPort": "8081"}]}
        )
        self.assertEqual(docker_utils.get_container_port(container), "1234")

    def test_get_container_port_multiple_exposed_ports(self):
        container = self._create_mock_container(ports={
            "80/tcp": [{"HostIp": "0.0.0.0", "HostPort": "8081"}],
            "443/tcp": [{"HostIp": "0.0.0.0", "HostPort": "8443"}]
        })
        self.assertIn(docker_utils.get_container_port(container), ["8081", "8443"])

    @patch('app.docker_utils.get_container_port', return_value="8080")
    def test_get_container_info_ignore_label_present(self, mock_get_port):
        mock_container = MagicMock()
        mock_container.name = "test-skip-app"
        mock_container.labels = {"dashy.skip": "true", "dashy.include": "true"}

        with patch.object(docker_utils, 'DASHY_EXPOSED_BY_DEFAULT', False), \
             patch.object(docker_utils, 'DOCKER_LABEL_PATTERN', re.compile(r"^dashy\.include$")), \
             patch.object(docker_utils, 'DOCKER_IGNORE_LABEL_PATTERN', re.compile(r"^dashy\.ignore$")):
            info = docker_utils.get_container_info(mock_container)
            self.assertIsNone(info)

    @patch('app.docker_utils.get_container_port', return_value="8080")
    def test_get_container_info_ignore_label_present_value_true(self, mock_get_port):
        mock_container = MagicMock()
        mock_container.name = "test-skip-app-true"
        mock_container.labels = {"dashy.skip": "true", "dashy.include": "true"}

        with patch.object(docker_utils, 'DASHY_EXPOSED_BY_DEFAULT', False), \
             patch.object(docker_utils, 'DOCKER_LABEL_PATTERN', re.compile(r"^dashy\.include$")), \
             patch.object(docker_utils, 'DOCKER_IGNORE_LABEL_PATTERN', re.compile(r"^dashy\.ignore$")):
            info = docker_utils.get_container_info(mock_container)
            self.assertIsNone(info)

    @patch('app.docker_utils.get_container_port', return_value="8080")
    def test_get_container_info_ignore_label_present_value_false(self, mock_get_port):
        mock_container = MagicMock()
        mock_container.name = "test-skip-app-false"
        mock_container.labels = {"dashy.skip": "false", "dashy.include": "true"}

        with patch.object(docker_utils, 'DASHY_EXPOSED_BY_DEFAULT', False), \
             patch.object(docker_utils, 'DOCKER_LABEL_PATTERN', re.compile(r"^dashy\.include$")), \
             patch.object(docker_utils, 'DOCKER_IGNORE_LABEL_PATTERN', re.compile(r"^dashy\.ignore$")):
            info = docker_utils.get_container_info(mock_container)
            self.assertIsNotNone(info)
            self.assertEqual(info["name"], "test-skip-app-false")

    @patch('app.docker_utils.get_container_port', return_value="8080")
    def test_get_container_info_ignore_label_present_value_other(self, mock_get_port):
        mock_container = MagicMock()
        mock_container.name = "test-skip-app-other"
        mock_container.labels = {"dashy.skip": "yes", "dashy.include": "true"}

        with patch.object(docker_utils, 'DASHY_EXPOSED_BY_DEFAULT', False), \
             patch.object(docker_utils, 'DOCKER_LABEL_PATTERN', re.compile(r"^dashy\.include$")), \
             patch.object(docker_utils, 'DOCKER_IGNORE_LABEL_PATTERN', re.compile(r"^dashy\.ignore$")):
            info = docker_utils.get_container_info(mock_container)
            self.assertIsNotNone(info)
            self.assertEqual(info["name"], "test-skip-app-other")
    
    @patch('app.docker_utils.get_container_port', return_value="8080")
    def test_get_container_info_ignore_label_present_value_true_case_insensitive(self, mock_get_port):
        mock_container = MagicMock()
        mock_container.name = "test-skip-app-True"
        mock_container.labels = {"dashy.skip": "TrUe", "dashy.include": "true"}

        with patch.object(docker_utils, 'DASHY_EXPOSED_BY_DEFAULT', False), \
             patch.object(docker_utils, 'DOCKER_LABEL_PATTERN', re.compile(r"^dashy\.include$")), \
             patch.object(docker_utils, 'DOCKER_IGNORE_LABEL_PATTERN', re.compile(r"^dashy\.ignore$")):
            info = docker_utils.get_container_info(mock_container)
            self.assertIsNone(info)

    @patch('app.docker_utils.get_container_port', return_value="8080")
    def test_get_container_info_ignore_label_present(self, mock_get_port):
        mock_container = MagicMock()
        mock_container.name = "test-ignore-app"
        mock_container.labels = {"dashy.ignore": "true", "dashy.include": "true"}

        with patch.object(docker_utils, 'DASHY_EXPOSED_BY_DEFAULT', False), \
             patch.object(docker_utils, 'DOCKER_LABEL_PATTERN', re.compile(r"^dashy\.include$")), \
             patch.object(docker_utils, 'DOCKER_IGNORE_LABEL_PATTERN', re.compile(r"^dashy\.ignore$")):
            info = docker_utils.get_container_info(mock_container)
            self.assertIsNone(info)

    @patch('app.docker_utils.get_container_port', return_value="8080")
    def test_get_container_info_ignore_label_present_value_true(self, mock_get_port):
        mock_container = MagicMock()
        mock_container.name = "test-ignore-app-true"
        mock_container.labels = {"dashy.ignore": "true", "dashy.include": "true"}

        with patch.object(docker_utils, 'DASHY_EXPOSED_BY_DEFAULT', False), \
             patch.object(docker_utils, 'DOCKER_LABEL_PATTERN', re.compile(r"^dashy\.include$")), \
             patch.object(docker_utils, 'DOCKER_IGNORE_LABEL_PATTERN', re.compile(r"^dashy\.ignore$")):
            info = docker_utils.get_container_info(mock_container)
            self.assertIsNone(info)

    @patch('app.docker_utils.get_container_port', return_value="8080")
    def test_get_container_info_ignore_label_present_value_false(self, mock_get_port):
        mock_container = MagicMock()
        mock_container.name = "test-ignore-app-false"
        mock_container.labels = {"dashy.ignore": "false", "dashy.include": "true"}

        with patch.object(docker_utils, 'DASHY_EXPOSED_BY_DEFAULT', False), \
             patch.object(docker_utils, 'DOCKER_LABEL_PATTERN', re.compile(r"^dashy\.include$")), \
             patch.object(docker_utils, 'DOCKER_IGNORE_LABEL_PATTERN', re.compile(r"^dashy\.ignore$")):
            info = docker_utils.get_container_info(mock_container)
            self.assertIsNotNone(info)
            self.assertEqual(info["name"], "test-ignore-app-false")

    @patch('app.docker_utils.get_container_port', return_value="8080")
    def test_get_container_info_ignore_label_present_value_other(self, mock_get_port):
        mock_container = MagicMock()
        mock_container.name = "test-ignore-app-other"
        mock_container.labels = {"dashy.ignore": "yes", "dashy.include": "true"}

        with patch.object(docker_utils, 'DASHY_EXPOSED_BY_DEFAULT', False), \
             patch.object(docker_utils, 'DOCKER_LABEL_PATTERN', re.compile(r"^dashy\.include$")), \
             patch.object(docker_utils, 'DOCKER_IGNORE_LABEL_PATTERN', re.compile(r"^dashy\.ignore$")):
            info = docker_utils.get_container_info(mock_container)
            self.assertIsNotNone(info)
            self.assertEqual(info["name"], "test-ignore-app-other")

    @patch('app.docker_utils.get_container_port', return_value="8080")
    def test_get_container_info_ignore_label_present_value_true_case_insensitive(self, mock_get_port):
        mock_container = MagicMock()
        mock_container.name = "test-ignore-app-True"
        mock_container.labels = {"dashy.ignore": "TrUe", "dashy.include": "true"}

        with patch.object(docker_utils, 'DASHY_EXPOSED_BY_DEFAULT', False), \
             patch.object(docker_utils, 'DOCKER_LABEL_PATTERN', re.compile(r"^dashy\.include$")), \
             patch.object(docker_utils, 'DOCKER_IGNORE_LABEL_PATTERN', re.compile(r"^dashy\.ignore$")):
            info = docker_utils.get_container_info(mock_container)
            self.assertIsNone(info)

    @patch('app.docker_utils.get_container_port', return_value="8080")
    def test_get_container_info_ignore_label_custom_regex_value_true(self, mock_get_port):
        mock_container = MagicMock()
        mock_container.name = "test-custom-ignore-app-true"
        mock_container.labels = {"custom.exclude.this": "true", "dashy.include": "true"}

        with patch.object(docker_utils, 'DASHY_EXPOSED_BY_DEFAULT', False), \
             patch.object(docker_utils, 'DOCKER_LABEL_PATTERN', re.compile(r"^dashy\.include$")), \
             patch.object(docker_utils, 'DOCKER_IGNORE_LABEL_PATTERN', re.compile(r"^custom\.exclude\.this$")):
            info = docker_utils.get_container_info(mock_container)
            self.assertIsNone(info)

    @patch('app.docker_utils.get_container_port', return_value="8080")
    def test_get_container_info_ignore_label_custom_regex_value_false(self, mock_get_port):
        mock_container = MagicMock()
        mock_container.name = "test-custom-ignore-app-false"
        mock_container.labels = {"custom.exclude.this": "false", "dashy.include": "true"}

        with patch.object(docker_utils, 'DASHY_EXPOSED_BY_DEFAULT', False), \
             patch.object(docker_utils, 'DOCKER_LABEL_PATTERN', re.compile(r"^dashy\.include$")), \
             patch.object(docker_utils, 'DOCKER_IGNORE_LABEL_PATTERN', re.compile(r"^custom\.exclude\.this$")):
            info = docker_utils.get_container_info(mock_container)
            self.assertIsNotNone(info)
            self.assertEqual(info["name"], "test-custom-ignore-app-false")

    @patch('app.docker_utils.get_container_port', return_value="8080")
    def test_get_container_info_exposed_by_default_but_ignored_value_true(self, mock_get_port):
        mock_container = MagicMock()
        mock_container.name = "test-exposed-but-ignored-true"
        mock_container.labels = {"dashy.ignore": "true"}

        with patch.object(docker_utils, 'DASHY_EXPOSED_BY_DEFAULT', True), \
             patch.object(docker_utils, 'DOCKER_LABEL_PATTERN', re.compile(r"^dashy\.include$")), \
             patch.object(docker_utils, 'DOCKER_IGNORE_LABEL_PATTERN', re.compile(r"^dashy\.ignore$")):
            info = docker_utils.get_container_info(mock_container)
            self.assertIsNone(info)

    @patch('app.docker_utils.get_container_port', return_value="8080")
    def test_get_container_info_exposed_by_default_ignore_label_value_false(self, mock_get_port):
        mock_container = MagicMock()
        mock_container.name = "test-exposed-ignore-false"
        mock_container.labels = {"dashy.ignore": "false"}

        with patch.object(docker_utils, 'DASHY_EXPOSED_BY_DEFAULT', True), \
             patch.object(docker_utils, 'DOCKER_LABEL_PATTERN', re.compile(r"^dashy\.include$")), \
             patch.object(docker_utils, 'DOCKER_IGNORE_LABEL_PATTERN', re.compile(r"^dashy\.ignore$")):
            info = docker_utils.get_container_info(mock_container)
            self.assertIsNotNone(info)
            self.assertEqual(info["name"], "test-exposed-ignore-false")

    @patch('app.docker_utils.get_container_port', return_value="8080")
    def test_get_container_info_ignore_label_custom_regex(self, mock_get_port):
        mock_container = MagicMock()
        mock_container.name = "test-custom-ignore-app"
        mock_container.labels = {"custom.exclude.this": "true", "dashy.include": "true"}

        with patch.object(docker_utils, 'DASHY_EXPOSED_BY_DEFAULT', False), \
             patch.object(docker_utils, 'DOCKER_LABEL_PATTERN', re.compile(r"^dashy\.include$")), \
             patch.object(docker_utils, 'DOCKER_IGNORE_LABEL_PATTERN', re.compile(r"^custom\.exclude\.this$")):
            info = docker_utils.get_container_info(mock_container)
            self.assertIsNone(info)

    @patch('app.docker_utils.get_container_port', return_value="8080")
    def test_get_container_info_exposed_by_default_but_ignored(self, mock_get_port):
        mock_container = MagicMock()
        mock_container.name = "test-exposed-but-ignored"
        mock_container.labels = {"dashy.ignore": "true"}

        with patch.object(docker_utils, 'DASHY_EXPOSED_BY_DEFAULT', True), \
             patch.object(docker_utils, 'DOCKER_LABEL_PATTERN', re.compile(r"^dashy\.include$")), \
             patch.object(docker_utils, 'DOCKER_IGNORE_LABEL_PATTERN', re.compile(r"^dashy\.ignore$")):
            info = docker_utils.get_container_info(mock_container)
            self.assertIsNone(info)

    @patch('app.docker_utils.get_container_port', return_value="8080")
    def test_get_container_info_no_ignore_label_included_by_label(self, mock_get_port):
        mock_container = MagicMock()
        mock_container.name = "test-app-include"
        mock_container.labels = {"dashy.include": "true"}

        with patch.object(docker_utils, 'DASHY_EXPOSED_BY_DEFAULT', False), \
             patch.object(docker_utils, 'DOCKER_LABEL_PATTERN', re.compile(r"^dashy\.include$")), \
             patch.object(docker_utils, 'DOCKER_IGNORE_LABEL_PATTERN', re.compile(r"^dashy\.ignore$")):
            info = docker_utils.get_container_info(mock_container)
            self.assertIsNotNone(info)
            self.assertEqual(info["name"], "test-app-include")

    @patch('app.docker_utils.get_container_port', return_value="8080")
    def test_get_container_info_no_ignore_label_exposed_by_default(self, mock_get_port):
        mock_container = MagicMock()
        mock_container.name = "test-app-exposed"
        mock_container.labels = {}

        with patch.object(docker_utils, 'DASHY_EXPOSED_BY_DEFAULT', True), \
             patch.object(docker_utils, 'DOCKER_LABEL_PATTERN', re.compile(r"^dashy\.include$")), \
             patch.object(docker_utils, 'DOCKER_IGNORE_LABEL_PATTERN', re.compile(r"^dashy\.ignore$")):
            info = docker_utils.get_container_info(mock_container)
            self.assertIsNotNone(info)
            self.assertEqual(info["name"], "test-app-exposed")

    def test_get_container_info_exposed_by_default_true(self):
        with patch.dict(os.environ, {"DASHY_EXPOSED_BY_DEFAULT": "true"}):
            import importlib
            importlib.reload(app_config)
            importlib.reload(docker_utils)

            with patch.object(docker_utils, 'get_container_port') as mock_get_port_inner:
                mock_get_port_inner.return_value = "8000"

                container = self._create_mock_container(name="service1")
                info = docker_utils.get_container_info(container)
                self.assertIsNotNone(info)
                self.assertEqual(info["name"], "service1")
                self.assertEqual(info["port"], "8000")
                mock_get_port_inner.assert_called_once_with(container)

    def test_get_container_info_exposed_by_label(self):
        with patch.dict(os.environ, {"DASHY_EXPOSED_BY_DEFAULT": "false"}):
            import importlib
            importlib.reload(app_config)
            importlib.reload(docker_utils)
            docker_utils.DOCKER_LABEL_PATTERN = re.compile(app_config.DASHY_DOCKER_LABEL_REGEX)

            with patch.object(docker_utils, 'get_container_port') as mock_get_port_inner:
                mock_get_port_inner.return_value = "8001"

                container = self._create_mock_container(name="service2", labels={"dashy.include": "true"})
                info = docker_utils.get_container_info(container)
                self.assertIsNotNone(info)
                self.assertEqual(info["name"], "service2")
                self.assertEqual(info["port"], "8001")

            container_custom = self._create_mock_container(name="service_custom", labels={"my.custom.label": "expose"})
            with patch.dict(os.environ, {"DASHY_DOCKER_LABEL_REGEX": r"^my\.custom\.label$"}):
                importlib.reload(app_config)
                importlib.reload(docker_utils)
                docker_utils.DOCKER_LABEL_PATTERN = re.compile(app_config.DASHY_DOCKER_LABEL_REGEX)

                with patch.object(docker_utils, 'get_container_port') as mock_get_port_custom:
                    mock_get_port_custom.return_value = "8002"
                    info_custom = docker_utils.get_container_info(container_custom)
                    self.assertIsNotNone(info_custom)
                    self.assertEqual(info_custom["name"], "service_custom")
                    self.assertEqual(info_custom["port"], "8002")
                    mock_get_port_custom.assert_called_once_with(container_custom)

    @patch('app.docker_utils.get_container_port')
    def test_get_container_info_not_exposed(self, mock_get_port):
        with patch.dict(os.environ, {"DASHY_EXPOSED_BY_DEFAULT": "false"}):
            import importlib
            importlib.reload(app_config)
            importlib.reload(docker_utils)

            container = self._create_mock_container(name="service3", labels={"other.label": "value"})
            info = docker_utils.get_container_info(container)
            self.assertIsNone(info)
            mock_get_port.assert_not_called()

    @patch('app.docker_utils.get_container_port', return_value=None)
    def test_get_container_info_port_extraction_fails(self, mock_get_port):
        with patch.dict(os.environ, {"DASHY_EXPOSED_BY_DEFAULT": "true"}):
            import importlib
            importlib.reload(app_config)
            importlib.reload(docker_utils)
            container = self._create_mock_container(name="service4")
            info = docker_utils.get_container_info(container)
            self.assertIsNotNone(info)
            self.assertEqual(info["name"], "service4")
            self.assertIsNone(info["port"])

    @classmethod
    def tearDownClass(cls):
        import importlib
        with patch.dict(os.environ, {}, clear=True):
            importlib.reload(app_config)
        importlib.reload(docker_utils)

if __name__ == '__main__':
    unittest.main()
