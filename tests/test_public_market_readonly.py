import ast
import asyncio
import builtins
import math
import time
import types
from pathlib import Path

import pandas as pd
import pytest

from src import public_market_readonly as m


REQ = {
    "mode": "real-readonly-dry-run",
    "provider": "akshare-public-market",
    "market": "cn-a",
    "instrumentType": "stock",
    "symbol": "600519",