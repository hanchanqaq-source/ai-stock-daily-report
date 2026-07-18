"""Schemas for local user profiles and quick stock/fund holdings."""

from typing import List, Optional

from pydantic import BaseModel, Field


class WorkspaceUserItem(BaseModel):
    id: str
    name: str
    is_primary: bool


class WorkspaceUserCreate(BaseModel):
    id: Optional[str] = Field(None, min_length=1, max_length=64, regex=r'^[A-Za-z0-9_-]+$')
    name: str = Field(..., min_length=1, max_length=24)


class WorkspaceUserRename(WorkspaceUserCreate):
    pass


class WorkspaceStockHoldingCreate(BaseModel):
    id: Optional[str] = Field(None, min_length=1, max_length=64, regex=r'^[A-Za-z0-9_-]+$')
    code: str = Field('', max_length=32)
    name: str = Field(..., min_length=1, max_length=100)
    quantity: float = Field(..., gt=0)
    average_cost: float = Field(..., ge=0)
    securities_account: str = Field('默认证券账户', min_length=1, max_length=100)
    notes: Optional[str] = Field(None, max_length=1000)


class WorkspaceStockHoldingItem(WorkspaceStockHoldingCreate):
    id: str


class WorkspaceFundHoldingCreate(BaseModel):
    id: Optional[str] = Field(None, min_length=1, max_length=64, regex=r'^[A-Za-z0-9_-]+$')
    code: str = Field('', max_length=32)
    name: str = Field(..., min_length=1, max_length=100)
    amount: float = Field(..., gt=0)
    profit: float = 0
    target_allocation: Optional[float] = Field(None, ge=0, le=100)
    notes: Optional[str] = Field(None, max_length=1000)


class WorkspaceFundHoldingItem(WorkspaceFundHoldingCreate):
    id: str


class WorkspacePortfolioState(BaseModel):
    users: List[WorkspaceUserItem]
    stock_holdings_by_user: dict[str, List[WorkspaceStockHoldingItem]]
    fund_holdings_by_user: dict[str, List[WorkspaceFundHoldingItem]]
