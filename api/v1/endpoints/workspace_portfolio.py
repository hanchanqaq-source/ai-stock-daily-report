"""Local-only persistence API for workspace profiles and quick holdings."""

import json
from datetime import datetime, timezone
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from api.deps import get_db
from api.v1.schemas.workspace_portfolio import (
    WorkspaceFundHoldingCreate,
    WorkspaceFundHoldingItem,
    WorkspacePortfolioBackupImportRequest,
    WorkspacePortfolioBackupImportResponse,
    WorkspacePortfolioBackupPayload,
    WorkspacePortfolioBackupPreview,
    WorkspacePortfolioRestorePointItem,
    WorkspacePortfolioRestoreRequest,
    WorkspacePortfolioState,
    WorkspaceStockHoldingCreate,
    WorkspaceStockHoldingItem,
    WorkspaceUserCreate,
    WorkspaceUserItem,
    WorkspaceUserRename,
)
from src.storage import WorkspaceFundHolding, WorkspacePortfolioBackup, WorkspaceStockHolding, WorkspaceUser

router = APIRouter()
PRIMARY_USER_ID = 'self'
BACKUP_FORMAT = 'dsa-workspace-portfolio-backup'
BACKUP_VERSION = 1
MAX_HOLDINGS_PER_DOMAIN = 1000


def _require_local(request: Request) -> None:
    host = request.client.host if request.client else ''
    if host not in {'127.0.0.1', '::1', 'testclient'}:
        raise HTTPException(status_code=403, detail='workspace_portfolio.localhost_only')


def _normalize_name(name: str) -> str:
    normalized = ' '.join(name.split())[:24]
    if not normalized:
        raise HTTPException(status_code=422, detail='workspace_portfolio.name_required')
    return normalized


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


def _user_item(row: WorkspaceUser) -> WorkspaceUserItem:
    return WorkspaceUserItem(id=row.id, name=row.name, is_primary=bool(row.is_primary))


def _state_from_db(db: Session) -> WorkspacePortfolioState:
    users = db.scalars(select(WorkspaceUser).order_by(WorkspaceUser.is_primary.desc(), WorkspaceUser.created_at)).all()
    stocks = db.scalars(select(WorkspaceStockHolding).order_by(WorkspaceStockHolding.created_at)).all()
    funds = db.scalars(select(WorkspaceFundHolding).order_by(WorkspaceFundHolding.created_at)).all()
    stock_map = {user.id: [] for user in users}
    fund_map = {user.id: [] for user in users}
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
    return WorkspacePortfolioState(users=[_user_item(row) for row in users], stock_holdings_by_user=stock_map, fund_holdings_by_user=fund_map)


def _backup_payload_from_state(state: WorkspacePortfolioState) -> WorkspacePortfolioBackupPayload:
    return WorkspacePortfolioBackupPayload(
        format=BACKUP_FORMAT,
        version=BACKUP_VERSION,
        exported_at=datetime.now(timezone.utc),
        users=state.users,
        stock_holdings_by_user=state.stock_holdings_by_user,
        fund_holdings_by_user=state.fund_holdings_by_user,
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
    stock_count = 0
    fund_count = 0
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
    if stock_count > MAX_HOLDINGS_PER_DOMAIN or fund_count > MAX_HOLDINGS_PER_DOMAIN:
        raise HTTPException(status_code=422, detail='workspace_portfolio.backup_too_large')
    return WorkspacePortfolioBackupPreview(users=len(backup.users), stock_holdings=stock_count, fund_holdings=fund_count, exported_at=backup.exported_at)


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
    db.execute(delete(WorkspaceUser))
    for user in backup.users:
        db.add(WorkspaceUser(id=user.id, name=_normalize_name(user.name), is_primary=user.is_primary))
    for user_id, holdings in backup.stock_holdings_by_user.items():
        for holding in holdings:
            db.add(WorkspaceStockHolding(user_id=user_id, **holding.model_dump()))
    for user_id, holdings in backup.fund_holdings_by_user.items():
        for holding in holdings:
            db.add(WorkspaceFundHolding(user_id=user_id, **holding.model_dump()))
    db.flush()
    return _state_from_db(db)


@router.get('', response_model=WorkspacePortfolioState)
def get_state(request: Request, db: Session = Depends(get_db)) -> WorkspacePortfolioState:
    _require_local(request)
    _ensure_primary(db)
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
    db.execute(delete(WorkspaceStockHolding).where(WorkspaceStockHolding.user_id == user_id))
    db.execute(delete(WorkspaceFundHolding).where(WorkspaceFundHolding.user_id == user_id))
    db.delete(row); db.commit()


@router.post('/users/{user_id}/stocks', response_model=WorkspaceStockHoldingItem, status_code=status.HTTP_201_CREATED)
def create_stock(user_id: str, payload: WorkspaceStockHoldingCreate, request: Request, db: Session = Depends(get_db)) -> WorkspaceStockHoldingItem:
    _require_local(request); _require_user(db, user_id)
    values = payload.model_dump(exclude={'id'})
    row = WorkspaceStockHolding(id=payload.id or f'stock-{uuid4().hex}', user_id=user_id, **values)
    db.add(row); db.commit(); db.refresh(row)
    return WorkspaceStockHoldingItem(id=row.id, **values)


@router.delete('/users/{user_id}/stocks/{holding_id}', status_code=status.HTTP_204_NO_CONTENT)
def remove_stock(user_id: str, holding_id: str, request: Request, db: Session = Depends(get_db)) -> None:
    _require_local(request); _require_user(db, user_id)
    row = db.get(WorkspaceStockHolding, holding_id)
    if row is None or row.user_id != user_id:
        raise HTTPException(status_code=404, detail='workspace_portfolio.holding_not_found')
    db.delete(row); db.commit()


@router.post('/users/{user_id}/funds', response_model=WorkspaceFundHoldingItem, status_code=status.HTTP_201_CREATED)
def create_fund(user_id: str, payload: WorkspaceFundHoldingCreate, request: Request, db: Session = Depends(get_db)) -> WorkspaceFundHoldingItem:
    _require_local(request); _require_user(db, user_id)
    values = payload.model_dump(exclude={'id'})
    row = WorkspaceFundHolding(id=payload.id or f'fund-{uuid4().hex}', user_id=user_id, **values)
    db.add(row); db.commit(); db.refresh(row)
    return WorkspaceFundHoldingItem(id=row.id, **values)


@router.delete('/users/{user_id}/funds/{holding_id}', status_code=status.HTTP_204_NO_CONTENT)
def remove_fund(user_id: str, holding_id: str, request: Request, db: Session = Depends(get_db)) -> None:
    _require_local(request); _require_user(db, user_id)
    row = db.get(WorkspaceFundHolding, holding_id)
    if row is None or row.user_id != user_id:
        raise HTTPException(status_code=404, detail='workspace_portfolio.holding_not_found')
    db.delete(row); db.commit()
