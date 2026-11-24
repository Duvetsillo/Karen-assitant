"""Model discovery resilience with deterministic workers and fake HTTP."""
import unittest
from unittest.mock import Mock, patch

from catalog import CatalogBroker, CatalogResult, CatalogSource, fetch_catalog


class CatalogTests(unittest.TestCase):
    def test_invalid_server_urls_return_errors_without_http_requests(self):
        for server in ('http://[broken', 'http://localhost:bad', 'http://localhost:99999',
                       'http://:11434', 'ftp://localhost', 'http://user:pass@localhost',
                       'http://localhost?token=secret', 'http://localhost#fragment'):
            with self.subTest(server=server), patch('catalog.requests.get') as get, patch('catalog.requests.post') as post:
                result = fetch_catalog(CatalogSource(server))
                self.assertEqual(result.status, 'error')
                self.assertNotIn('secret', result.message)
                get.assert_not_called()
                post.assert_not_called()

    def test_invalid_optional_cloud_metadata_preserves_local_models(self):
        source = CatalogSource('http://127.0.0.1:11434')
        for capabilities in (None, 42, 'completion', {'completion': True}, []):
            with self.subTest(capabilities=capabilities):
                local = Mock()
                local.json.return_value = {'models': [{'name': 'local'}]}
                cloud = Mock(status_code=200)
                cloud.json.return_value = {'capabilities': capabilities}
                with patch('catalog.requests.get', return_value=local), patch('catalog.requests.post', return_value=cloud):
                    result = fetch_catalog(source)
                self.assertEqual(result.status, 'ready')
                self.assertEqual(result.models, ({'name': 'local'},))
                cloud.json.assert_called_once_with()

    def test_valid_optional_cloud_model_remains_selectable(self):
        local, cloud = Mock(), Mock(status_code=200)
        local.json.return_value = {'models': []}
        cloud.json.return_value = {'capabilities': ['completion']}
        with patch('catalog.requests.get', return_value=local), patch('catalog.requests.post', return_value=cloud):
            result = fetch_catalog(CatalogSource('http://localhost:11434'))
        self.assertEqual(result.status, 'ready')
        self.assertEqual(result.models[0]['name'], 'gemma4:31b-cloud')

    def test_failed_listener_does_not_block_other_waiters_or_cache(self):
        source = CatalogSource('http://127.0.0.1:11434')
        result = CatalogResult(({'name': 'local'},), 'ready', 'Disponible')
        broker = CatalogBroker(fetcher=Mock(return_value=result))
        broken, healthy = Mock(side_effect=RuntimeError('closed UI')), Mock()
        with patch('catalog.threading.Thread') as thread:
            broker.request(source, broken)
            broker.request(source, healthy)
            worker = thread.call_args.kwargs['target']
            with self.assertLogs('catalog', level='ERROR'):
                worker()
        healthy.assert_called_once_with(result)
        cached = Mock()
        broker.request(source, cached)
        cached.assert_called_once_with(result)
        self.assertFalse(broker.inflight)
