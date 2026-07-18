"""Integration tests for Build E1 local workspace persistence."""

import os
import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from api.app import create_app
from src.config import Config
from src.storage import DatabaseManager


class WorkspacePortfolioApiTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / 'workspace.db'
        os.environ['DATABASE_PATH'] = str(self.db_path)
        Config.reset_instance()
        DatabaseManager.reset_instance()
        self.client = TestClient(create_app(static_dir=Path(self.temp_dir.name) / 'static'))

    def tearDown(self) -> None:
        DatabaseManager.reset_instance()
        Config.reset_instance()
        os.environ.pop('DATABASE_PATH', None)
        self.temp_dir.cleanup()

    def test_state_survives_backend_restart_and_keeps_domains_separate(self) -> None:
        initial = self.client.get('/api/v1/workspace-portfolio')
        self.assertEqual(initial.status_code, 200, initial.text)
        self.assertEqual(initial.json()['users'][0], {'id': 'self', 'name': '本人', 'is_primary': True})

        user = {'id': 'user-family-a', 'name': '家人A'}
        self.assertEqual(self.client.post('/api/v1/workspace-portfolio/users', json=user).status_code, 201)
        stock = {'id': 'stock-a', 'code': '600519', 'name': '贵州茅台', 'quantity': 2, 'average_cost': 1500, 'securities_account': '账户A'}
        fund = {'id': 'fund-a', 'code': '000001', 'name': '测试基金', 'amount': 1000, 'profit': 20, 'target_allocation': 30}
        self.assertEqual(self.client.post('/api/v1/workspace-portfolio/users/user-family-a/stocks', json=stock).status_code, 201)
        self.assertEqual(self.client.post('/api/v1/workspace-portfolio/users/user-family-a/funds', json=fund).status_code, 201)

        DatabaseManager.reset_instance()
        Config.reset_instance()
        self.client = TestClient(create_app(static_dir=Path(self.temp_dir.name) / 'static-after-restart'))
        restored = self.client.get('/api/v1/workspace-portfolio').json()
        self.assertEqual(restored['stock_holdings_by_user']['user-family-a'][0]['code'], '600519')
        self.assertEqual(restored['fund_holdings_by_user']['user-family-a'][0]['code'], '000001')
        self.assertEqual(restored['stock_holdings_by_user']['self'], [])
        self.assertEqual(restored['fund_holdings_by_user']['self'], [])

    def test_deleting_secondary_user_cascades_quick_holdings_and_protects_primary(self) -> None:
        self.client.get('/api/v1/workspace-portfolio')
        self.client.post('/api/v1/workspace-portfolio/users', json={'id': 'user-delete', 'name': '待删除'})
        self.client.post('/api/v1/workspace-portfolio/users/user-delete/stocks', json={
            'id': 'stock-delete', 'code': 'AAPL', 'name': 'Apple', 'quantity': 1,
            'average_cost': 100, 'securities_account': '账户B',
        })
        self.assertEqual(self.client.delete('/api/v1/workspace-portfolio/users/self').status_code, 409)
        self.assertEqual(self.client.delete('/api/v1/workspace-portfolio/users/user-delete').status_code, 204)
        state = self.client.get('/api/v1/workspace-portfolio').json()
        self.assertNotIn('user-delete', {item['id'] for item in state['users']})
        self.assertNotIn('user-delete', state['stock_holdings_by_user'])


if __name__ == '__main__':
    unittest.main()
