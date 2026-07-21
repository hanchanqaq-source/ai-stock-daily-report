"""Integration tests for the local workspace persistence stages."""

import os
import sqlite3
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

    def restart_backend(self, suffix: str = 'restart') -> None:
        DatabaseManager.reset_instance()
        Config.reset_instance()
        self.client = TestClient(create_app(static_dir=Path(self.temp_dir.name) / f'static-{suffix}'))

    def tearDown(self) -> None:
        DatabaseManager.reset_instance()
        Config.reset_instance()
        os.environ.pop('DATABASE_PATH', None)
        self.temp_dir.cleanup()

    def test_workspace_schema_is_the_only_portfolio_persistence_source(self) -> None:
        self.assertEqual(self.client.get('/api/v1/workspace-portfolio').status_code, 200)
        with sqlite3.connect(self.db_path) as connection:
            tables = {
                row[0]
                for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")
            }
        self.assertTrue({
            'schema_migrations',
            'workspace_users',
            'workspace_portfolio_preferences',
            'workspace_stock_holdings',
            'workspace_fund_holdings',
            'workspace_fund_watchlist_items',
            'workspace_portfolio_backups',
            'workspace_holding_recycle_entries',
            'workspace_holding_history_entries',
        }.issubset(tables))
        self.assertTrue({
            'users', 'stock_holdings', 'fund_holdings', 'schema_version', 'data_migrations',
        }.isdisjoint(tables))
        self.assertFalse((self.db_path.parent / 'stock_fund_quality.db').exists())

    def test_fund_watchlist_crud_restart_user_isolation_and_holding_separation(self) -> None:
        self.client.get('/api/v1/workspace-portfolio')
        self.client.post('/api/v1/workspace-portfolio/users', json={'id': 'user-watch-a', 'name': '自选用户A'})
        self.client.post('/api/v1/workspace-portfolio/users', json={'id': 'user-watch-b', 'name': '自选用户B'})
        watch_item = {'id': 'fund-watch-a', 'code': '000001', 'name': '测试自选基金', 'notes': '等待观察'}
        created = self.client.post('/api/v1/workspace-portfolio/users/user-watch-a/fund-watchlist', json=watch_item)
        self.assertEqual(created.status_code, 201, created.text)
        self.assertEqual(self.client.post(
            '/api/v1/workspace-portfolio/users/user-watch-a/fund-watchlist',
            json={'id': 'fund-watch-duplicate', 'code': '000001', 'name': '重复基金'},
        ).status_code, 409)
        self.assertEqual(self.client.post(
            '/api/v1/workspace-portfolio/users/user-watch-b/fund-watchlist',
            json={'id': 'fund-watch-b', 'code': '000001', 'name': '另一个用户可以关注'},
        ).status_code, 201)
        self.assertEqual(self.client.post(
            '/api/v1/workspace-portfolio/users/user-watch-a/funds',
            json={'id': 'fund-holding-a', 'code': '000001', 'name': '同代码持仓', 'amount': 1000, 'profit': 10},
        ).status_code, 201)
        self.assertEqual(self.client.post(
            '/api/v1/workspace-portfolio/users/user-watch-a/fund-watchlist',
            json={'id': 'invalid-code', 'code': 'ABC', 'name': '非法代码'},
        ).status_code, 422)

        self.restart_backend('fund-watchlist-restart')
        state = self.client.get('/api/v1/workspace-portfolio').json()
        self.assertEqual(state['fund_watchlist_by_user']['user-watch-a'][0]['notes'], '等待观察')
        self.assertEqual(state['fund_watchlist_by_user']['user-watch-b'][0]['code'], '000001')
        self.assertEqual(state['fund_holdings_by_user']['user-watch-a'][0]['id'], 'fund-holding-a')
        self.assertEqual(state['fund_watchlist_by_user']['self'], [])

        updated = self.client.patch(
            '/api/v1/workspace-portfolio/users/user-watch-a/fund-watchlist/fund-watch-a',
            json={'code': '000002', 'name': '已更新自选基金', 'notes': '继续观察'},
        )
        self.assertEqual(updated.status_code, 200, updated.text)
        self.assertEqual(updated.json()['name'], '已更新自选基金')
        self.assertEqual(self.client.patch(
            '/api/v1/workspace-portfolio/users/user-watch-b/fund-watchlist/fund-watch-a',
            json={'code': '000002', 'name': '越权修改'},
        ).status_code, 404)
        self.assertEqual(self.client.delete(
            '/api/v1/workspace-portfolio/users/user-watch-b/fund-watchlist/fund-watch-a',
        ).status_code, 404)
        self.assertEqual(self.client.delete(
            '/api/v1/workspace-portfolio/users/user-watch-a/fund-watchlist/fund-watch-a',
        ).status_code, 204)
        state = self.client.get('/api/v1/workspace-portfolio').json()
        self.assertEqual(state['fund_watchlist_by_user']['user-watch-a'], [])
        self.assertEqual(state['fund_holdings_by_user']['user-watch-a'][0]['id'], 'fund-holding-a')

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

        self.restart_backend('holdings-restart')
        restored = self.client.get('/api/v1/workspace-portfolio').json()
        self.assertEqual(restored['stock_holdings_by_user']['user-family-a'][0]['code'], '600519')
        self.assertEqual(restored['fund_holdings_by_user']['user-family-a'][0]['code'], '000001')
        self.assertEqual(restored['stock_holdings_by_user']['self'], [])
        self.assertEqual(restored['fund_holdings_by_user']['self'], [])

    def test_active_user_selection_survives_restart_and_resets_if_user_is_removed(self) -> None:
        self.client.get('/api/v1/workspace-portfolio')
        self.client.post('/api/v1/workspace-portfolio/users', json={'id': 'user-active', 'name': '当前用户'})
        renamed = self.client.patch('/api/v1/workspace-portfolio/users/user-active', json={'name': '已改名用户'})
        self.assertEqual(renamed.status_code, 200, renamed.text)
        self.assertEqual(renamed.json()['name'], '已改名用户')
        selected = self.client.put('/api/v1/workspace-portfolio/active-user/user-active')
        self.assertEqual(selected.status_code, 200, selected.text)
        self.assertEqual(selected.json()['active_user_id'], 'user-active')

        self.restart_backend('active-user-restart')
        restarted = self.client.get('/api/v1/workspace-portfolio').json()
        self.assertEqual(restarted['active_user_id'], 'user-active')
        self.assertEqual(next(user for user in restarted['users'] if user['id'] == 'user-active')['name'], '已改名用户')
        self.assertEqual(self.client.delete('/api/v1/workspace-portfolio/users/user-active').status_code, 204)
        self.assertEqual(self.client.get('/api/v1/workspace-portfolio').json()['active_user_id'], 'self')

    def test_stock_crud_restart_recycle_history_and_domain_isolation(self) -> None:
        self.client.get('/api/v1/workspace-portfolio')
        self.client.post('/api/v1/workspace-portfolio/users', json={'id': 'user-stock', 'name': '股票用户'})
        created = self.client.post('/api/v1/workspace-portfolio/users/user-stock/stocks', json={
            'id': 'stock-persist', 'code': '600519', 'name': '测试股票', 'quantity': 1,
            'average_cost': 100, 'securities_account': '账户A', 'notes': '初始备注',
        })
        self.assertEqual(created.status_code, 201, created.text)
        self.client.post('/api/v1/workspace-portfolio/users/user-stock/funds', json={
            'id': 'fund-neighbor', 'code': '000001', 'name': '隔离基金', 'amount': 1000, 'profit': 10,
        })
        updated = self.client.patch('/api/v1/workspace-portfolio/users/user-stock/stocks/stock-persist', json={
            'code': '600519', 'name': '测试股票', 'quantity': 3, 'average_cost': 120,
            'securities_account': '账户B', 'notes': '重启后仍需存在',
        })
        self.assertEqual(updated.status_code, 200, updated.text)

        self.restart_backend('stock-restart')
        state = self.client.get('/api/v1/workspace-portfolio').json()
        stock = state['stock_holdings_by_user']['user-stock'][0]
        self.assertEqual((stock['quantity'], stock['average_cost'], stock['securities_account'], stock['notes']), (3, 120, '账户B', '重启后仍需存在'))
        self.assertEqual(state['fund_holdings_by_user']['user-stock'][0]['id'], 'fund-neighbor')
        self.assertEqual(state['stock_holdings_by_user']['self'], [])

        deleted = self.client.delete('/api/v1/workspace-portfolio/users/user-stock/stocks/stock-persist')
        self.assertEqual(deleted.status_code, 204, deleted.text)
        state = self.client.get('/api/v1/workspace-portfolio').json()
        self.assertEqual(state['stock_holdings_by_user']['user-stock'], [])
        self.assertEqual(state['fund_holdings_by_user']['user-stock'][0]['id'], 'fund-neighbor')
        recycle = self.client.get('/api/v1/workspace-portfolio/users/user-stock/recycle-bin').json()
        self.assertEqual((recycle[0]['asset_type'], recycle[0]['holding']['id']), ('stock', 'stock-persist'))
        history = self.client.get('/api/v1/workspace-portfolio/users/user-stock/holding-history?asset_type=stock').json()
        self.assertEqual({item['action'] for item in history}, {'created', 'updated', 'deleted'})

    def test_fund_crud_restart_recycle_history_and_domain_isolation(self) -> None:
        self.client.get('/api/v1/workspace-portfolio')
        self.client.post('/api/v1/workspace-portfolio/users', json={'id': 'user-fund', 'name': '基金用户'})
        created = self.client.post('/api/v1/workspace-portfolio/users/user-fund/funds', json={
            'id': 'fund-persist', 'code': '000001', 'name': '测试基金', 'amount': 1000,
            'profit': 10, 'target_allocation': 20, 'notes': '初始备注',
        })
        self.assertEqual(created.status_code, 201, created.text)
        self.client.post('/api/v1/workspace-portfolio/users/user-fund/stocks', json={
            'id': 'stock-neighbor', 'code': 'AAPL', 'name': '隔离股票', 'quantity': 1,
            'average_cost': 100, 'securities_account': '账户A',
        })
        updated = self.client.patch('/api/v1/workspace-portfolio/users/user-fund/funds/fund-persist', json={
            'code': '000001', 'name': '测试基金', 'amount': 2500, 'profit': 80,
            'target_allocation': 35, 'notes': '重启后仍需存在',
        })
        self.assertEqual(updated.status_code, 200, updated.text)

        self.restart_backend('fund-restart')
        state = self.client.get('/api/v1/workspace-portfolio').json()
        fund = state['fund_holdings_by_user']['user-fund'][0]
        self.assertEqual((fund['amount'], fund['profit'], fund['target_allocation'], fund['notes']), (2500, 80, 35, '重启后仍需存在'))
        self.assertEqual(state['stock_holdings_by_user']['user-fund'][0]['id'], 'stock-neighbor')
        self.assertEqual(state['fund_holdings_by_user']['self'], [])

        deleted = self.client.delete('/api/v1/workspace-portfolio/users/user-fund/funds/fund-persist')
        self.assertEqual(deleted.status_code, 204, deleted.text)
        state = self.client.get('/api/v1/workspace-portfolio').json()
        self.assertEqual(state['fund_holdings_by_user']['user-fund'], [])
        self.assertEqual(state['stock_holdings_by_user']['user-fund'][0]['id'], 'stock-neighbor')
        recycle = self.client.get('/api/v1/workspace-portfolio/users/user-fund/recycle-bin').json()
        self.assertEqual((recycle[0]['asset_type'], recycle[0]['holding']['id']), ('fund', 'fund-persist'))
        history = self.client.get('/api/v1/workspace-portfolio/users/user-fund/holding-history?asset_type=fund').json()
        self.assertEqual({item['action'] for item in history}, {'created', 'updated', 'deleted'})

    def test_deleting_secondary_user_cascades_quick_holdings_and_protects_primary(self) -> None:
        self.client.get('/api/v1/workspace-portfolio')
        self.client.post('/api/v1/workspace-portfolio/users', json={'id': 'user-delete', 'name': '待删除'})
        self.client.post('/api/v1/workspace-portfolio/users/user-delete/stocks', json={
            'id': 'stock-delete', 'code': 'AAPL', 'name': 'Apple', 'quantity': 1,
            'average_cost': 100, 'securities_account': '账户B',
        })
        self.client.post('/api/v1/workspace-portfolio/users/user-delete/fund-watchlist', json={
            'id': 'fund-watch-delete', 'code': '000001', 'name': '待删除自选基金',
        })
        self.assertEqual(self.client.delete('/api/v1/workspace-portfolio/users/self').status_code, 409)
        self.assertEqual(self.client.delete('/api/v1/workspace-portfolio/users/user-delete').status_code, 204)
        state = self.client.get('/api/v1/workspace-portfolio').json()
        self.assertNotIn('user-delete', {item['id'] for item in state['users']})
        self.assertNotIn('user-delete', state['stock_holdings_by_user'])
        self.assertNotIn('user-delete', state['fund_watchlist_by_user'])

    def test_backup_preview_import_and_restore_keep_only_workspace_data(self) -> None:
        self.client.get('/api/v1/workspace-portfolio')
        self.client.post('/api/v1/workspace-portfolio/users', json={'id': 'user-backup', 'name': '备份用户'})
        self.client.post('/api/v1/workspace-portfolio/users/user-backup/stocks', json={
            'id': 'stock-backup', 'code': '600519', 'name': '贵州茅台', 'quantity': 2,
            'average_cost': 1500, 'securities_account': '账户A',
        })
        self.client.post('/api/v1/workspace-portfolio/users/user-backup/fund-watchlist', json={
            'id': 'fund-watch-backup', 'code': '000001', 'name': '备份自选基金', 'notes': '备份备注',
        })
        exported = self.client.get('/api/v1/workspace-portfolio/backup/export')
        self.assertEqual(exported.status_code, 200, exported.text)
        backup = exported.json()
        self.assertEqual(backup['format'], 'dsa-workspace-portfolio-backup')
        self.assertEqual(set(backup), {'format', 'version', 'exported_at', 'users', 'stock_holdings_by_user', 'fund_holdings_by_user', 'fund_watchlist_by_user'})
        preview = self.client.post('/api/v1/workspace-portfolio/backup/preview', json=backup)
        self.assertEqual(preview.status_code, 200, preview.text)
        self.assertEqual(preview.json()['stock_holdings'], 1)
        self.assertEqual(preview.json()['fund_watchlist_items'], 1)

        self.client.post('/api/v1/workspace-portfolio/users/self/funds', json={
            'id': 'fund-current', 'code': '000001', 'name': '当前基金', 'amount': 2000, 'profit': 30,
        })
        self.client.post('/api/v1/workspace-portfolio/users/self/fund-watchlist', json={
            'id': 'fund-watch-current', 'code': '110022', 'name': '当前自选基金',
        })
        rejected = self.client.post('/api/v1/workspace-portfolio/backup/import', json={'backup': backup, 'confirmed': False})
        self.assertEqual(rejected.status_code, 409)
        self.assertEqual(self.client.get('/api/v1/workspace-portfolio').json()['fund_holdings_by_user']['self'][0]['id'], 'fund-current')

        imported = self.client.post('/api/v1/workspace-portfolio/backup/import', json={'backup': backup, 'confirmed': True})
        self.assertEqual(imported.status_code, 200, imported.text)
        self.assertEqual(imported.json()['state']['stock_holdings_by_user']['user-backup'][0]['id'], 'stock-backup')
        self.assertEqual(imported.json()['state']['fund_holdings_by_user']['self'], [])
        self.assertEqual(imported.json()['state']['fund_watchlist_by_user']['user-backup'][0]['id'], 'fund-watch-backup')
        self.assertEqual(imported.json()['state']['fund_watchlist_by_user']['self'], [])
        restore_points = self.client.get('/api/v1/workspace-portfolio/backup/restore-points').json()
        self.assertEqual(restore_points[0]['reason'], 'before_import')

        restored = self.client.post(f"/api/v1/workspace-portfolio/backup/restore-points/{restore_points[0]['id']}", json={'confirmed': True})
        self.assertEqual(restored.status_code, 200, restored.text)
        self.assertEqual(restored.json()['state']['fund_holdings_by_user']['self'][0]['id'], 'fund-current')
        self.assertEqual(restored.json()['state']['fund_watchlist_by_user']['self'][0]['id'], 'fund-watch-current')

    def test_backup_rejects_unknown_users_and_unknown_fields(self) -> None:
        backup = self.client.get('/api/v1/workspace-portfolio/backup/export').json()
        backup['stock_holdings_by_user']['unknown-user'] = []
        self.assertEqual(self.client.post('/api/v1/workspace-portfolio/backup/preview', json=backup).status_code, 422)

    def test_legacy_backup_without_fund_watchlist_remains_importable(self) -> None:
        backup = self.client.get('/api/v1/workspace-portfolio/backup/export').json()
        backup.pop('fund_watchlist_by_user')
        preview = self.client.post('/api/v1/workspace-portfolio/backup/preview', json=backup)
        self.assertEqual(preview.status_code, 200, preview.text)
        self.assertEqual(preview.json()['fund_watchlist_items'], 0)

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
        updated = next(item for item in fund_history.json() if item['action'] == 'updated')
        self.assertEqual(updated['previous_holding']['amount'], 1000)
        self.assertEqual(updated['holding']['amount'], 1500)
        self.assertEqual(self.client.get('/api/v1/workspace-portfolio/users/user-history/holding-history?asset_type=other').status_code, 422)
        self.assertEqual(self.client.get('/api/v1/workspace-portfolio/users/self/holding-history').json(), [])


if __name__ == '__main__':
    unittest.main()
