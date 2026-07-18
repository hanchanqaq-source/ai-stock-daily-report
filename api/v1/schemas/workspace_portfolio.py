"""Schemas for local user profiles and quick stock/fund holdings."""

from datetime import datetime
from typing import List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


class WorkspaceBackupModel(BaseModel):
    """Strict, finite JSON contract for local workspace backup files."""

    model_config = ConfigDict(extra='forbid', allow_inf_nan=False)


class WorkspaceUserItem(WorkspaceBackupModel):
    id: str = Field(..., min_length=1, max_length=64, pattern=r'^[A-Za-z0-9_-]+$')
    name: str = Field(..., min_length=1, max_length=24)
    is_primary: bool


class WorkspaceUserCreate(BaseModel):
    id: Optional[str] = Field(None, min_length=1, max_length=64, pattern=r'^[A-Za-z0-9_-]+$')
    name: str = Field(..., min_length=1, max_length=24)


class WorkspaceUserRename(WorkspaceUserCreate):
    pass


class WorkspaceStockHoldingCreate(WorkspaceBackupModel):
    id: Optional[str] = Field(None, min_length=1, max_length=64, pattern=r'^[A-Za-z0-9_-]+$')
    code: str = Field('', max_length=32)
    name: str = Field(..., min_length=1, max_length=100)
    quantity: float = Field(..., gt=0)
    average_cost: float = Field(..., ge=0)
    securities_account: str = Field('默认证券账户', min_length=1, max_length=100)
    notes: Optional[str] = Field(None, max_length=1000)


class WorkspaceStockHoldingItem(WorkspaceStockHoldingCreate):
    id: str = Field(..., min_length=1, max_length=64, pattern=r'^[A-Za-z0-9_-]+$')


class WorkspaceFundHoldingCreate(WorkspaceBackupModel):
    id: Optional[str] = Field(None, min_length=1, max_length=64, pattern=r'^[A-Za-z0-9_-]+$')
    code: str = Field('', max_length=32)
    name: str = Field(..., min_length=1, max_length=100)
    amount: float = Field(..., gt=0)
    profit: float = 0
    target_allocation: Optional[float] = Field(None, ge=0, le=100)
    notes: Optional[str] = Field(None, max_length=1000)


class WorkspaceFundHoldingItem(WorkspaceFundHoldingCreate):
    id: str = Field(..., min_length=1, max_length=64, pattern=r'^[A-Za-z0-9_-]+$')


class WorkspacePortfolioState(WorkspaceBackupModel):
    users: List[WorkspaceUserItem]
    stock_holdings_by_user: dict[str, List[WorkspaceStockHoldingItem]]
    fund_holdings_by_user: dict[str, List[WorkspaceFundHoldingItem]]


class WorkspacePortfolioBackupPayload(WorkspaceBackupModel):
    format: Literal['dsa-workspace-portfolio-backup']
    version: Literal[1]
    exported_at: datetime
    users: List[WorkspaceUserItem] = Field(..., max_length=50)
    stock_holdings_by_user: dict[str, List[WorkspaceStockHoldingItem]]
    fund_holdings_by_user: dict[str, List[WorkspaceFundHoldingItem]]


class WorkspacePortfolioBackupPreview(WorkspaceBackupModel):
    users: int
    stock_holdings: int
    fund_holdings: int
    exported_at: datetime
    will_replace_current_workspace: bool = True


class WorkspacePortfolioBackupImportRequest(WorkspaceBackupModel):
    backup: WorkspacePortfolioBackupPayload
    confirmed: bool = False


class WorkspacePortfolioBackupImportResponse(WorkspaceBackupModel):
    state: WorkspacePortfolioState
    restore_point_id: str


class WorkspacePortfolioRestorePointItem(WorkspaceBackupModel):
    id: str
    reason: Literal['before_import', 'before_restore']
    created_at: str


class WorkspacePortfolioRestoreRequest(WorkspaceBackupModel):
    confirmed: bool = False


class WorkspaceHoldingRecycleItem(WorkspaceBackupModel):
    id: str
    asset_type: Literal['stock', 'fund']
    holding: WorkspaceStockHoldingItem | WorkspaceFundHoldingItem
    created_at: str
