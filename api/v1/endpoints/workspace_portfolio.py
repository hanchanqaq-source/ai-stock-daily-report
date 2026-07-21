"""Local-only persistence API for workspace profiles and quick holdings."""

import json
from datetime import datetime, timezone
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import delete, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from api.deps import get_db
from api.v1.schemas.workspace_portfolio import (
    WorkspaceFundHoldingCreate,
    WorkspaceFundHoldingItem,
    WorkspaceFundWatchlistCreate,
    WorkspaceFundWatchlistItem,
    WorkspacePortfolioBackupImportRequest,
    WorkspacePortfolioBackupImportResponse,
    WorkspacePortfolioBackupPayload,
    WorkspacePortfolioBackupPreview,
    WorkspacePortfolioRestorePointItem,
    WorkspacePortfolioRestoreRequest,
    WorkspaceHoldingRecycleItem,
    WorkspaceHoldingHistoryItem,
    WorkspacePortfolioState,
    WorkspaceStockHoldingCreate,
    WorkspaceStockHoldingItem,
    WorkspaceUserCreate,
    WorkspaceUserItem,
    WorkspaceUserRename,
)
from src.storage import WorkspaceFundHolding, WorkspaceFundWatchlistItem as WorkspaceFundWatchlistRow, WorkspaceHoldingHistoryEntry, WorkspaceHoldingRecycleEntry, WorkspacePortfolioBackup, WorkspacePortfolioPreference, WorkspaceStockHolding, WorkspaceUser

router = APIRouter()
PRIMARY_USER_ID = 'self'
BACKUP_FORMAT = 'dsa-workspace-portfolio-backup'
BACKUP_VERSION = 1
MAX_HOLDINGS_PER_DOMAIN = 1000
MAX_FUND_WATCHLIST_ITEMS = 1000
ACTIVE_USER_PREFERENCE_KEY = 'active_user_id'


def _require_local(request: Request) -> None:
    host = request.client.host if request.client else ''
    if host not in {'127.0.0.1', '::1', 'testclient'}:
        raise HTTPException(status_code=403, detail='workspace_portfolio.localhost_only')


def _normalize_name(name: str) -> str:
    normalized = ' '.join(name.split())[:24]
    if not normalized:
        raise HTTPException(status_code=422, detail='workspace_portfolio.name_required')
    return normalized


def _normalize_fund_watchlist_values(payload: WorkspaceFundWatchlistCreate) -> dict[str, str | None]:
    name = ' '.join(payload.name.split())[:100]
    if not name:
        raise HTTPException(status_code=422, detail='workspace_portfolio.fund_watchlist_name_required')
    notes = payload.notes.strip() if payload.notes else None
    return {'code': payload.code, 'name': name, 'notes': notes or None}


def _ensure_primary(db: Session) -> WorkspaceUser:
    primary = db.get(WorkspaceUser, PRIMARY_USER_ID)
    if primary is None:
        primary = WorkspaceUser(id=PRIMARY_USER_ID, name='本人', is_primary=True)
        db.add(primary)
        db.commit()
        db.refresh(primary)
    return primary


def _require_user(db: Session, user_id: str) -> WorkspaceUser:
    user = db.get(WorkspaceUser, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail='workspace_portfolio.user_not_found')
    return user


def _active_user_id(db: Session, users: list[WorkspaceUser]) -> str:
    """Return a valid saved active user; legacy databases safely fall back to 本人."""
    valid_ids = {user.id for user in users}
    preference = db.get(WorkspacePortfolioPreference, ACTIVE_USER_PREFERENCE_KEY)
    if preference and preference.value in valid_ids:
        return preference.value
    return PRIMARY_USER_ID


def _save_active_user_id(db: Session, user_id: str) -> None:
    _require_user(db, user_id)
    preference = db.get(WorkspacePortfolioPreference, ACTIVE_USER_PREFERENCE_KEY)
    if preference is None:
        db.add(WorkspacePortfolioPreference(key=ACTIVE_USER_PREFERENCE_KEY, value=user_id))
    else:
        preference.value = user_id
    db.flush()


def _user_item(row: WorkspaceUser) -> WorkspaceUserItem:
    return WorkspaceUserItem(id=row.id, name=row.name, is_primary=bool(row.is_primary))


def _state_from_db(db: Session) -> WorkspacePortfolioState:
    users = db.scalars(select(WorkspaceUser).order_by(WorkspaceUser.is_primary.desc(), WorkspaceUser.created_at)).all()
    stocks = db.scalars(select(WorkspaceStockHolding).order_by(WorkspaceStockHolding.created_at)).all()
    funds = db.scalars(select(WorkspaceFundHolding).order_by(WorkspaceFundHolding.created_at)).all()
    fund_watchlist = db.scalars(
        select(WorkspaceFundWatchlistRow).order_by(WorkspaceFundWatchlistRow.created_at)
    ).all()
    stock_map = {user.id: [] for user in users}
    fund_map = {user.id: [] for user in users}
    fund_watchlist_map = {user.id: [] for user in users}
    for row in stocks:
        stock_map.setdefault(row.user_id, []).append(WorkspaceStockHoldingItem(
            id=row.id, code=row.code, name=row.name, quantity=row.quantity,
            average_cost=row.average_cost, securities_account=row.securities_account, notes=row.notes,
        ))
    for row in funds:
        fund_map.setdefault(row.user_id, []).append(WorkspaceFundHoldingItem(
            id=row.id, code=row.code, name=row.name, amount=row.amount, profit=row.profit,
            target_allocation=row.target_allocation, notes=row.notes,
        ))
    for row in fund_watchlist:
        fund_watchlist_map.setdefault(row.user_id, []).append(WorkspaceFundWatchlistItem(
            id=row.id, code=row.code, name=row.name, notes=row.notes,
        ))
    return WorkspacePortfolioState(
        users=[_user_item(row) for row in users],
        active_user_id=_active_user_id(db, users),
        stock_holdings_by_user=stock_map,
        fund_holdings_by_user=fund_map,
        fund_watchlist_by_user=fund_watchlist_map,
    )


def _backup_payload_from_state(state: WorkspacePortfolioState) -> WorkspacePortfolioBackupPayload:
    return WorkspacePortfolioBackupPayload(
        format=BACKUP_FORMAT,
        version=BACKUP_VERSION,
        exported_at=datetime.now(timezone.utc),
        users=state.users,
        stock_holdings_by_user=state.stock_holdings_by_user,
        fund_holdings_by_user=state.fund_holdings_by_user,
        fund_watchlist_by_user=state.fund_watchlist_by_user,
    )


def _validate_backup(backup: WorkspacePortfolioBackupPayload) -> WorkspacePortfolioBackupPreview:
    user_ids = {user.id for user in backup.users}
    if len(user_ids) != len(backup.users) or PRIMARY_USER_ID not in user_ids:
        raise HTTPException(status_code=422, detail='workspace_portfolio.backup_invalid_users')
    primaries = [user for user in backup.users if user.is_primary]
    if len(primaries) != 1 or primaries[0].id != PRIMARY_USER_ID:
        raise HTTPException(status_code=422, detail='workspace_portfolio.backup_primary_required')
    stock_ids: set[str] = set()
    fund_ids: set[str] = set()
    fund_watchlist_ids: set[str] = set()
    stock_count = 0
    fund_count = 0
    fund_watchlist_count = 0
    for user_id, holdings in backup.stock_holdings_by_user.items():
        if user_id not in user_ids or len(holdings) > MAX_HOLDINGS_PER_DOMAIN:
            raise HTTPException(status_code=422, detail='workspace_portfolio.backup_invalid_stock_map')
        for holding in holdings:
            if holding.id in stock_ids:
                raise HTTPException(status_code=422, detail='workspace_portfolio.backup_duplicate_stock_id')
            stock_ids.add(holding.id); stock_count += 1
    for user_id, holdings in backup.fund_holdings_by_user.items():
        if user_id not in user_ids or len(holdings) > MAX_HOLDINGS_PER_DOMAIN:
            raise HTTPException(status_code=422, detail='workspace_portfolio.backup_invalid_fund_map')
        for holding in holdings:
            if holding.id in fund_ids:
                raise HTTPException(status_code=422, detail='workspace_portfolio.backup_duplicate_fund_id')
            fund_ids.add(holding.id); fund_count += 1
    for user_id, items in backup.fund_watchlist_by_user.items():
        if user_id not in user_ids or len(items) > MAX_FUND_WATCHLIST_ITEMS:
            raise HTTPException(status_code=422, detail='workspace_portfolio.backup_invalid_fund_watchlist_map')
        codes: set[str] = set()
        for item in items:
            if item.id in fund_watchlist_ids:
                raise HTTPException(status_code=422, detail='workspace_portfolio.backup_duplicate_fund_watchlist_id')
            if item.code in codes:
                raise HTTPException(status_code=422, detail='workspace_portfolio.backup_duplicate_fund_watchlist_code')
            fund_watchlist_ids.add(item.id)
            codes.add(item.code)
            fund_watchlist_count += 1
    if stock_count > MAX_HOLDINGS_PER_DOMAIN or fund_count > MAX_HOLDINGS_PER_DOMAIN or fund_watchlist_count > MAX_FUND_WATCHLIST_ITEMS:
        raise HTTPException(status_code=422, detail='workspace_portfolio.backup_too_large')
    return WorkspacePortfolioBackupPreview(
        users=len(backup.users),
        stock_holdings=stock_count,
        fund_holdings=fund_count,
        fund_watchlist_items=fund_watchlist_count,
        exported_at=backup.exported_at,
    )


def _save_restore_point(db: Session, state: WorkspacePortfolioState, reason: str) -> str:
    restore_point_id = f'workspace-backup-{uuid4().hex}'
    payload = _backup_payload_from_state(state)
    db.add(WorkspacePortfolioBackup(
        id=restore_point_id,
        reason=reason,
        snapshot_json=json.dumps(payload.model_dump(mode='json'), ensure_ascii=False, separators=(',', ':')),
    ))
    return restore_point_id


def _replace_state(db: Session, backup: WorkspacePortfolioBackupPayload) -> WorkspacePortfolioState:
    db.execute(delete(WorkspaceStockHolding))
    db.execute(delete(WorkspaceFundHolding))
    db.execute(delete(WorkspaceFundWatchlistRow))
    db.execute(delete(WorkspaceUser))
    for user in backup.users:
        db.add(WorkspaceUser(id=user.id, name=_normalize_name(user.name), is_primary=user.is_primary))
    for user_id, holdings in backup.stock_holdings_by_user.items():
        for holding in holdings:
            db.add(WorkspaceStockHolding(user_id=user_id, **holding.model_dump()))
    for user_id, holdings in backup.fund_holdings_by_user.items():
        for holding in holdings:
            db.add(WorkspaceFundHolding(user_id=user_id, **holding.model_dump()))
    for user_id, items in backup.fund_watchlist_by_user.items():
        for item in items:
            db.add(WorkspaceFundWatchlistRow(user_id=user_id, **item.model_dump()))
    db.flush()
    _save_active_user_id(db, PRIMARY_USER_ID)
    return _state_from_db(db)


def _recycle_holding(db: Session, user_id: str, asset_type: str, holding: WorkspaceStockHoldingItem | WorkspaceFundHoldingItem) -> None:
    db.add(WorkspaceHoldingRecycleEntry(id=f'recycle-{uuid4().hex}', user_id=user_id, asset_type=asset_type, holding_json=holding.model_dump_json()))


def _record_holding_history(db: Session, user_id: str, asset_type: str, action: str, holding: WorkspaceStockHoldingItem | WorkspaceFundHoldingItem, previous_holding: WorkspaceStockHoldingItem | WorkspaceFundHoldingItem | None = None) -> None:
    payload = holding.model_dump_json() if previous_holding is None else json.dumps({'before': previous_holding.model_dump(mode='json'), 'after': holding.model_dump(mode='json')}, ensure_ascii=False, separators=(',', ':'))
    db.add(WorkspaceHoldingHistoryEntry(id=f'history-{uuid4().hex}', user_id=user_id, asset_type=asset_type, action=action, holding_json=payload))


def _history_item(row: WorkspaceHoldingHistoryEntry) -> WorkspaceHoldingHistoryItem:
    raw = json.loads(row.holding_json)
    if isinstance(raw, dict) and 'before' in raw and 'after' in raw:
        previous_json = json.dumps(raw['before'], ensure_ascii=False)
        holding_json = json.dumps(raw['after'], ensure_ascii=False)
    else:
        previous_json = None
        holding_json = row.holding_json
    parser = WorkspaceStockHoldingItem if row.asset_type == 'stock' else WorkspaceFundHoldingItem
    return WorkspaceHoldingHistoryItem(id=row.id, asset_type=row.asset_type, action=row.action, holding=parser.model_validate_json(holding_json), previous_holding=(parser.model_validate_json(previous_json) if previous_json else None), created_at=row.created_at.replace(tzinfo=timezone.utc).isoformat())


@router.get('', response_model=WorkspacePortfolioState)
def get_state(request: Request, db: Session = Depends(get_db)) -> WorkspacePortfolioState:
    _require_local(request)
    _ensure_primary(db)
    return _state_from_db(db)


@router.put('/active-user/{user_id}', response_model=WorkspacePortfolioState)
def set_active_user(user_id: str, request: Request, db: Session = Depends(get_db)) -> WorkspacePortfolioState:
    _require_local(request)
    _ensure_primary(db)
    _save_active_user_id(db, user_id)
    db.commit()
    return _state_from_db(db)


@router.get('/backup/export', response_model=WorkspacePortfolioBackupPayload)
def export_backup(request: Request, db: Session = Depends(get_db)) -> WorkspacePortfolioBackupPayload:
    _require_local(request)
    _ensure_primary(db)
    return _backup_payload_from_state(_state_from_db(db))


@router.post('/backup/preview', response_model=WorkspacePortfolioBackupPreview)
def preview_backup(backup: WorkspacePortfolioBackupPayload, request: Request) -> WorkspacePortfolioBackupPreview:
    _require_local(request)
    return _validate_backup(backup)


@router.post('/backup/import', response_model=WorkspacePortfolioBackupImportResponse)
def import_backup(payload: WorkspacePortfolioBackupImportRequest, request: Request, db: Session = Depends(get_db)) -> WorkspacePortfolioBackupImportResponse:
    _require_local(request)
    if not payload.confirmed:
        raise HTTPException(status_code=409, detail='workspace_portfolio.import_confirmation_required')
    _validate_backup(payload.backup)
    _ensure_primary(db)
    restore_point_id = _save_restore_point(db, _state_from_db(db), 'before_import')
    state = _replace_state(db, payload.backup)
    db.commit()
    return WorkspacePortfolioBackupImportResponse(state=state, restore_point_id=restore_point_id)


@router.get('/backup/restore-points', response_model=list[WorkspacePortfolioRestorePointItem])
def list_restore_points(request: Request, db: Session = Depends(get_db)) -> list[WorkspacePortfolioRestorePointItem]:
    _require_local(request)
    rows = db.scalars(select(WorkspacePortfolioBackup).order_by(WorkspacePortfolioBackup.created_at.desc()).limit(10)).all()
    return [WorkspacePortfolioRestorePointItem(id=row.id, reason=row.reason, created_at=row.created_at.replace(tzinfo=timezone.utc).isoformat()) for row in rows]


@router.post('/backup/restore-points/{restore_point_id}', response_model=WorkspacePortfolioBackupImportResponse)
def restore_backup(restore_point_id: str, payload: WorkspacePortfolioRestoreRequest, request: Request, db: Session = Depends(get_db)) -> WorkspacePortfolioBackupImportResponse:
    _require_local(request)
    if not payload.confirmed:
        raise HTTPException(status_code=409, detail='workspace_portfolio.restore_confirmation_required')
    row = db.get(WorkspacePortfolioBackup, restore_point_id)
    if row is None:
        raise HTTPException(status_code=404, detail='workspace_portfolio.restore_point_not_found')
    try:
        backup = WorkspacePortfolioBackupPayload.model_validate_json(row.snapshot_json)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail='workspace_portfolio.restore_point_invalid') from exc
    _validate_backup(backup)
    _ensure_primary(db)
    new_restore_point_id = _save_restore_point(db, _state_from_db(db), 'before_restore')
    state = _replace_state(db, backup)
    db.commit()
    return WorkspacePortfolioBackupImportResponse(state=state, restore_point_id=new_restore_point_id)


@router.post('/users', response_model=WorkspaceUserItem, status_code=status.HTTP_201_CREATED)
def create_user(payload: WorkspaceUserCreate, request: Request, db: Session = Depends(get_db)) -> WorkspaceUserItem:
    _require_local(request)
    _ensure_primary(db)
    row = WorkspaceUser(id=payload.id or f'user-{uuid4().hex}', name=_normalize_name(payload.name), is_primary=False)
    db.add(row); db.commit(); db.refresh(row)
    return _user_item(row)


@router.patch('/users/{user_id}', response_model=WorkspaceUserItem)
def rename_user(user_id: str, payload: WorkspaceUserRename, request: Request, db: Session = Depends(get_db)) -> WorkspaceUserItem:
    _require_local(request)
    row = _require_user(db, user_id)
    row.name = _normalize_name(payload.name)
    db.commit(); db.refresh(row)
    return _user_item(row)


@router.delete('/users/{user_id}', status_code=status.HTTP_204_NO_CONTENT)
def remove_user(user_id: str, request: Request, db: Session = Depends(get_db)) -> None:
    _require_local(request)
    row = _require_user(db, user_id)
    if row.is_primary:
        raise HTTPException(status_code=409, detail='workspace_portfolio.primary_user_protected')
    preference = db.get(WorkspacePortfolioPreference, ACTIVE_USER_PREFERENCE_KEY)
    if preference and preference.value == user_id:
        preference.value = PRIMARY_USER_ID
    db.execute(delete(WorkspaceStockHolding).where(WorkspaceStockHolding.user_id == user_id))
    db.execute(delete(WorkspaceFundHolding).where(WorkspaceFundHolding.user_id == user_id))
    db.execute(delete(WorkspaceFundWatchlistRow).where(WorkspaceFundWatchlistRow.user_id == user_id))
    db.delete(row); db.commit()


@router.post('/users/{user_id}/fund-watchlist', response_model=WorkspaceFundWatchlistItem, status_code=status.HTTP_201_CREATED)
def create_fund_watchlist_item(user_id: str, payload: WorkspaceFundWatchlistCreate, request: Request, db: Session = Depends(get_db)) -> WorkspaceFundWatchlistItem:
    _require_local(request); _require_user(db, user_id)
    item_count = db.scalar(select(func.count()).select_from(WorkspaceFundWatchlistRow).where(WorkspaceFundWatchlistRow.user_id == user_id)) or 0
    if item_count >= MAX_FUND_WATCHLIST_ITEMS:
        raise HTTPException(status_code=409, detail='workspace_portfolio.fund_watchlist_limit_reached')
    values = _normalize_fund_watchlist_values(payload)
    existing = db.scalar(select(WorkspaceFundWatchlistRow).where(
        WorkspaceFundWatchlistRow.user_id == user_id,
        WorkspaceFundWatchlistRow.code == values['code'],
    ))
    if existing is not None:
        raise HTTPException(status_code=409, detail='workspace_portfolio.fund_watchlist_duplicate')
    row = WorkspaceFundWatchlistRow(
        id=payload.id or f'fund-watch-{uuid4().hex}',
        user_id=user_id,
        **values,
    )
    db.add(row)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail='workspace_portfolio.fund_watchlist_conflict') from exc
    return WorkspaceFundWatchlistItem(id=row.id, **values)


@router.patch('/users/{user_id}/fund-watchlist/{item_id}', response_model=WorkspaceFundWatchlistItem)
def update_fund_watchlist_item(user_id: str, item_id: str, payload: WorkspaceFundWatchlistCreate, request: Request, db: Session = Depends(get_db)) -> WorkspaceFundWatchlistItem:
    _require_local(request); _require_user(db, user_id)
    row = db.get(WorkspaceFundWatchlistRow, item_id)
    if row is None or row.user_id != user_id:
        raise HTTPException(status_code=404, detail='workspace_portfolio.fund_watchlist_item_not_found')
    values = _normalize_fund_watchlist_values(payload)
    duplicate = db.scalar(select(WorkspaceFundWatchlistRow).where(
        WorkspaceFundWatchlistRow.user_id == user_id,
        WorkspaceFundWatchlistRow.code == values['code'],
        WorkspaceFundWatchlistRow.id != item_id,
    ))
    if duplicate is not None:
        raise HTTPException(status_code=409, detail='workspace_portfolio.fund_watchlist_duplicate')
    for key, value in values.items():
        setattr(row, key, value)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail='workspace_portfolio.fund_watchlist_conflict') from exc
    return WorkspaceFundWatchlistItem(id=row.id, **values)


@router.delete('/users/{user_id}/fund-watchlist/{item_id}', status_code=status.HTTP_204_NO_CONTENT)
def remove_fund_watchlist_item(user_id: str, item_id: str, request: Request, db: Session = Depends(get_db)) -> None:
    _require_local(request); _require_user(db, user_id)
    row = db.get(WorkspaceFundWatchlistRow, item_id)
    if row is None or row.user_id != user_id:
        raise HTTPException(status_code=404, detail='workspace_portfolio.fund_watchlist_item_not_found')
    db.delete(row); db.commit()


@router.post('/users/{user_id}/stocks', response_model=WorkspaceStockHoldingItem, status_code=status.HTTP_201_CREATED)
def create_stock(user_id: str, payload: WorkspaceStockHoldingCreate, request: Request, db: Session = Depends(get_db)) -> WorkspaceStockHoldingItem:
    _require_local(request); _require_user(db, user_id)
    values = payload.model_dump(exclude={'id'})
    row = WorkspaceStockHolding(id=payload.id or f'stock-{uuid4().hex}', user_id=user_id, **values)
    item = WorkspaceStockHoldingItem(id=row.id, **values)
    db.add(row); _record_holding_history(db, user_id, 'stock', 'created', item); db.commit(); db.refresh(row)
    return item


@router.delete('/users/{user_id}/stocks/{holding_id}', status_code=status.HTTP_204_NO_CONTENT)
def remove_stock(user_id: str, holding_id: str, request: Request, db: Session = Depends(get_db)) -> None:
    _require_local(request); _require_user(db, user_id)
    row = db.get(WorkspaceStockHolding, holding_id)
    if row is None or row.user_id != user_id:
        raise HTTPException(status_code=404, detail='workspace_portfolio.holding_not_found')
    item = WorkspaceStockHoldingItem(id=row.id, code=row.code, name=row.name, quantity=row.quantity, average_cost=row.average_cost, securities_account=row.securities_account, notes=row.notes)
    _recycle_holding(db, user_id, 'stock', item); _record_holding_history(db, user_id, 'stock', 'deleted', item)
    db.delete(row); db.commit()


@router.patch('/users/{user_id}/stocks/{holding_id}', response_model=WorkspaceStockHoldingItem)
def update_stock(user_id: str, holding_id: str, payload: WorkspaceStockHoldingCreate, request: Request, db: Session = Depends(get_db)) -> WorkspaceStockHoldingItem:
    _require_local(request); _require_user(db, user_id)
    row = db.get(WorkspaceStockHolding, holding_id)
    if row is None or row.user_id != user_id:
        raise HTTPException(status_code=404, detail='workspace_portfolio.holding_not_found')
    before = WorkspaceStockHoldingItem(id=row.id, code=row.code, name=row.name, quantity=row.quantity, average_cost=row.average_cost, securities_account=row.securities_account, notes=row.notes)
    values = payload.model_dump(exclude={'id'})
    for key, value in values.items():
        setattr(row, key, value)
    item = WorkspaceStockHoldingItem(id=row.id, **values)
    _record_holding_history(db, user_id, 'stock', 'updated', item, before); db.commit(); db.refresh(row)
    return item


@router.post('/users/{user_id}/funds', response_model=WorkspaceFundHoldingItem, status_code=status.HTTP_201_CREATED)
def create_fund(user_id: str, payload: WorkspaceFundHoldingCreate, request: Request, db: Session = Depends(get_db)) -> WorkspaceFundHoldingItem:
    _require_local(request); _require_user(db, user_id)
    values = payload.model_dump(exclude={'id'})
    row = WorkspaceFundHolding(id=payload.id or f'fund-{uuid4().hex}', user_id=user_id, **values)
    item = WorkspaceFundHoldingItem(id=row.id, **values)
    db.add(row); _record_holding_history(db, user_id, 'fund', 'created', item); db.commit(); db.refresh(row)
    return item


@router.delete('/users/{user_id}/funds/{holding_id}', status_code=status.HTTP_204_NO_CONTENT)
def remove_fund(user_id: str, holding_id: str, request: Request, db: Session = Depends(get_db)) -> None:
    _require_local(request); _require_user(db, user_id)
    row = db.get(WorkspaceFundHolding, holding_id)
    if row is None or row.user_id != user_id:
        raise HTTPException(status_code=404, detail='workspace_portfolio.holding_not_found')
    item = WorkspaceFundHoldingItem(id=row.id, code=row.code, name=row.name, amount=row.amount, profit=row.profit, target_allocation=row.target_allocation, notes=row.notes)
    _recycle_holding(db, user_id, 'fund', item); _record_holding_history(db, user_id, 'fund', 'deleted', item)
    db.delete(row); db.commit()


@router.get('/users/{user_id}/recycle-bin', response_model=list[WorkspaceHoldingRecycleItem])
def list_recycle_bin(user_id: str, request: Request, db: Session = Depends(get_db)) -> list[WorkspaceHoldingRecycleItem]:
    _require_local(request); _require_user(db, user_id)
    rows = db.scalars(select(WorkspaceHoldingRecycleEntry).where(WorkspaceHoldingRecycleEntry.user_id == user_id).order_by(WorkspaceHoldingRecycleEntry.created_at.desc()).limit(20)).all()
    return [WorkspaceHoldingRecycleItem(id=row.id, asset_type=row.asset_type, holding=(WorkspaceStockHoldingItem.model_validate_json(row.holding_json) if row.asset_type == 'stock' else WorkspaceFundHoldingItem.model_validate_json(row.holding_json)), created_at=row.created_at.replace(tzinfo=timezone.utc).isoformat()) for row in rows]


@router.get('/users/{user_id}/holding-history', response_model=list[WorkspaceHoldingHistoryItem])
def list_holding_history(user_id: str, request: Request, asset_type: str | None = None, db: Session = Depends(get_db)) -> list[WorkspaceHoldingHistoryItem]:
    _require_local(request); _require_user(db, user_id)
    if asset_type not in {None, 'stock', 'fund'}:
        raise HTTPException(status_code=422, detail='workspace_portfolio.invalid_asset_type')
    query = select(WorkspaceHoldingHistoryEntry).where(WorkspaceHoldingHistoryEntry.user_id == user_id)
    if asset_type:
        query = query.where(WorkspaceHoldingHistoryEntry.asset_type == asset_type)
    rows = db.scalars(query.order_by(WorkspaceHoldingHistoryEntry.created_at.desc()).limit(50)).all()
    return [_history_item(row) for row in rows]


@router.post('/users/{user_id}/recycle-bin/{entry_id}/restore', response_model=WorkspaceStockHoldingItem | WorkspaceFundHoldingItem)
def restore_recycled_holding(user_id: str, entry_id: str, request: Request, db: Session = Depends(get_db)) -> WorkspaceStockHoldingItem | WorkspaceFundHoldingItem:
    _require_local(request); _require_user(db, user_id)
    row = db.get(WorkspaceHoldingRecycleEntry, entry_id)
    if row is None or row.user_id != user_id: raise HTTPException(status_code=404, detail='workspace_portfolio.recycle_entry_not_found')
    asset_type = row.asset_type
    if asset_type == 'stock':
        holding = WorkspaceStockHoldingItem.model_validate_json(row.holding_json)
        if db.get(WorkspaceStockHolding, holding.id): raise HTTPException(status_code=409, detail='workspace_portfolio.holding_id_conflict')
        db.add(WorkspaceStockHolding(user_id=user_id, **holding.model_dump()))
    else:
        holding = WorkspaceFundHoldingItem.model_validate_json(row.holding_json)
        if db.get(WorkspaceFundHolding, holding.id): raise HTTPException(status_code=409, detail='workspace_portfolio.holding_id_conflict')
        db.add(WorkspaceFundHolding(user_id=user_id, **holding.model_dump()))
    db.delete(row); _record_holding_history(db, user_id, asset_type, 'restored', holding); db.commit()
    return holding


@router.patch('/users/{user_id}/funds/{holding_id}', response_model=WorkspaceFundHoldingItem)
def update_fund(user_id: str, holding_id: str, payload: WorkspaceFundHoldingCreate, request: Request, db: Session = Depends(get_db)) -> WorkspaceFundHoldingItem:
    _require_local(request); _require_user(db, user_id)
    row = db.get(WorkspaceFundHolding, holding_id)
    if row is None or row.user_id != user_id:
        raise HTTPException(status_code=404, detail='workspace_portfolio.holding_not_found')
    before = WorkspaceFundHoldingItem(id=row.id, code=row.code, name=row.name, amount=row.amount, profit=row.profit, target_allocation=row.target_allocation, notes=row.notes)
    values = payload.model_dump(exclude={'id'})
    for key, value in values.items():
        setattr(row, key, value)
    item = WorkspaceFundHoldingItem(id=row.id, **values)
    _record_holding_history(db, user_id, 'fund', 'updated', item, before); db.commit(); db.refresh(row)
    return item
