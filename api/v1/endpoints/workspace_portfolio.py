"""Local-only persistence API for workspace profiles and quick holdings."""

from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from api.deps import get_db
from api.v1.schemas.workspace_portfolio import (
    WorkspaceFundHoldingCreate,
    WorkspaceFundHoldingItem,
    WorkspacePortfolioState,
    WorkspaceStockHoldingCreate,
    WorkspaceStockHoldingItem,
    WorkspaceUserCreate,
    WorkspaceUserItem,
    WorkspaceUserRename,
)
from src.storage import WorkspaceFundHolding, WorkspaceStockHolding, WorkspaceUser

router = APIRouter()
PRIMARY_USER_ID = 'self'


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


@router.get('', response_model=WorkspacePortfolioState)
def get_state(request: Request, db: Session = Depends(get_db)) -> WorkspacePortfolioState:
    _require_local(request)
    _ensure_primary(db)
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
    values = payload.dict(exclude={'id'})
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
    values = payload.dict(exclude={'id'})
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
