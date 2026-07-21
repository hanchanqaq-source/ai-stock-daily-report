# -*- coding: utf-8 -*-
"""
===================================
数据访问层模块初始化
===================================

职责：
1. 声明可导出的 Repository 类（延迟导入，避免导入轻量子模块时拉入 pandas/SQLAlchemy 等重依赖）
"""


def __getattr__(name: str):
    """Lazy-load repository classes only when accessed from this package."""
    _lazy_map = {
        "AnalysisRepository": "src.repositories.analysis_repo",
        "BacktestRepository": "src.repositories.backtest_repo",
        "DecisionSignalRepository": "src.repositories.decision_signal_repo",
        "DecisionSignalOutcomeRepository": "src.repositories.decision_signal_outcome_repo",
        "StockRepository": "src.repositories.stock_repo",
    }
    if name in _lazy_map:
        import importlib
        module = importlib.import_module(_lazy_map[name])
        return getattr(module, name)
    raise AttributeError(f"module 'src.repositories' has no attribute {name!r}")


__all__ = [
    "AnalysisRepository",
    "BacktestRepository",
    "DecisionSignalRepository",
    "DecisionSignalOutcomeRepository",
    "StockRepository",
]
