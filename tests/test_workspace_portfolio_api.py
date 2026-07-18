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

    def test_backup_preview_import_and_restore_keep_only_workspace_data(self) -> None:
        self.client.get('/api/v1/workspace-portfolio')
        self.client.post('/api/v1/workspace-portfolio/users', json={'id': 'user-backup', 'name': '备份用户'})
        self.client.post('/api/v1/workspace-portfolio/users/user-backup/stocks', json={
            'id': 'stock-backup', 'code': '600519', 'name': '贵州茅台', 'quantity': 2,
            'average_cost': 1500, 'securities_account': '账户A',
        })
        exported = self.client.get('/api/v1/workspace-portfolio/backup/export')
        self.assertEqual(exported.status_code, 200, exported.text)
        backup = exported.json()
        self.assertEqual(backup['format'], 'dsa-workspace-portfolio-backup')
        self.assertEqual(set(backup), {'format', 'version', 'exported_at', 'users', 'stock_holdings_by_user', 'fund_holdings_by_user'})
        preview = self.client.post('/api/v1/workspace-portfolio/backup/preview', json=backup)
        self.assertEqual(preview.status_code, 200, preview.text)
        self.assertEqual(preview.json()['stock_holdings'], 1)

        self.client.post('/api/v1/workspace-portfolio/users/self/funds', json={
            'id': 'fund-current', 'code': '000001', 'name': '当前基金', 'amount': 2000, 'profit': 30,
        })
        rejected = self.client.post('/api/v1/workspace-portfolio/backup/import', json={'backup': backup, 'confirmed': False})
        self.assertEqual(rejected.status_code, 409)
        self.assertEqual(self.client.get('/api/v1/workspace-portfolio').json()['fund_holdings_by_user']['self'][0]['id'], 'fund-current')

        imported = self.client.post('/api/v1/workspace-portfolio/backup/import', json={'backup': backup, 'confirmed': True})
        self.assertEqual(imported.status_code, 200, imported.text)
        self.assertEqual(imported.json()['state']['stock_holdings_by_user']['user-backup'][0]['id'], 'stock-backup')
        self.assertEqual(imported.json()['state']['fund_holdings_by_user']['self'], [])
        restore_points = self.client.get('/api/v1/workspace-portfolio/backup/restore-points').json()
        self.assertEqual(restore_points[0]['reason'], 'before_import')

        restored = self.client.post(f"/api/v1/workspace-portfolio/backup/restore-points/{restore_points[0]['id']}", json={'confirmed': True})
        self.assertEqual(restored.status_code, 200, restored.text)
        self.assertEqual(restored.json()['state']['fund_holdings_by_user']['self'][0]['id'], 'fund-current')

    def test_backup_rejects_unknown_users_and_unknown_fields(self) -> None:
        backup = self.client.get('/api/v1/workspace-portfolio/backup/export').json()
        backup['stock_holdings_by_user']['unknown-user'] = []
        self.assertEqual(self.client.post('/api/v1/workspace-portfolio/backup/preview', json=backup).status_code, 422)

    def test_editing_quick_holdings_keeps_domains_and_users_isolated(self) -> None:
        self.client.get('/api/v1/workspace-portfolio')
        self.client.post('/api/v1/workspace-portfolio/users', json={'id': 'user-edit', 'name': '编辑用户'})
        self.client.post('/api/v1/workspace-portfolio/users/user-edit/stocks', json={
            'id': 'stock-edit', 'code': '600519', 'name': '原股票', 'quantity': 1, 'average_cost': 100, 'securities_account': '账户A',
        })
        self.client.post('/api/v1/workspace-portfolio/users/user-edit/funds', json={
            'id': 'fund-edit', 'code': '000001', 'name': '原基金', 'amount': 1000, 'profit': 10,
        })
        stock_update = self.client.patch('/api/v1/workspace-portfolio/users/user-edit/stocks/stock-edit', json={
            'code': '600519', 'name': '已编辑股票', 'quantity': 3, 'average_cost': 120, 'securities_account': '账户B', 'notes': '已核对',
        })
        self.assertEqual(stock_update.status_code, 200, stock_update.text)
        self.assertEqual(stock_update.json()['quantity'], 3)
        self.assertEqual(self.client.patch('/api/v1/workspace-portfolio/users/self/stocks/stock-edit', json={
            'code': '600519', 'name': '越权修改', 'quantity': 2, 'average_cost': 100, 'securities_account': '账户A',
        }).status_code, 404)
        fund_update = self.client.patch('/api/v1/workspace-portfolio/users/user-edit/funds/fund-edit', json={
            'code': '000001', 'name': '已编辑基金', 'amount': 2000, 'profit': 50, 'target_allocation': 40,
        })
        self.assertEqual(fund_update.status_code, 200, fund_update.text)
        state = self.client.get('/api/v1/workspace-portfolio').json()
        self.assertEqual(state['stock_holdings_by_user']['user-edit'][0]['name'], '已编辑股票')
        self.assertEqual(state['fund_holdings_by_user']['user-edit'][0]['name'], '已编辑基金')
        backup = self.client.get('/api/v1/workspace-portfolio/backup/export').json()
        backup['secret'] = 'must-not-be-accepted'
        self.assertEqual(self.client.post('/api/v1/workspace-portfolio/backup/preview', json=backup).status_code, 422)

    def test_holding_history_is_user_scoped_and_records_mutations(self) -> None:
        self.client.get('/api/v1/workspace-portfolio')
        self.client.post('/api/v1/workspace-portfolio/users', json={'id': 'user-history', 'name': '历史用户'})
        payload = {'id': 'fund-history', 'code': '000001', 'name': '历史基金', 'amount': 1000, 'profit': 10}
        self.assertEqual(self.client.post('/api/v1/workspace-portfolio/users/user-history/funds', json=payload).status_code, 201)
        payload['amount'] = 1500
        self.assertEqual(self.client.patch('/api/v1/workspace-portfolio/users/user-history/funds/fund-history', json=payload).status_code, 200)
        self.assertEqual(self.client.delete('/api/v1/workspace-portfolio/users/user-history/funds/fund-history').status_code, 204)
        self.assertEqual(self.client.post('/api/v1/workspace-portfolio/users/user-history/stocks', json={
            'id': 'stock-history', 'code': '600519', 'name': '历史股票', 'quantity': 1, 'average_cost': 1500, 'securities_account': '账户A',
        }).status_code, 201)
        history = self.client.get('/api/v1/workspace-portfolio/users/user-history/holding-history')
        self.assertEqual(history.status_code, 200, history.text)
        self.assertEqual({item['action'] for item in history.json()}, {'created', 'updated', 'deleted'})
        self.assertEqual({item['asset_type'] for item in history.json()}, {'fund', 'stock'})
        fund_history = self.client.get('/api/v1/workspace-portfolio/users/user-history/holding-history?asset_type=fund')
        self.assertEqual({item['asset_type'] for item in fund_history.json()}, {'fund'})
        self.assertEqual(self.client.get('/api/v1/workspace-portfolio/users/user-history/holding-history?asset_type=other').status_code, 422)
        self.assertEqual(self.client.get('/api/v1/workspace-portfolio/users/self/holding-history').json(), [])


if __name__ == '__main__':
    unittest.main()
