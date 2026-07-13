import ast
import asyncio
import math
import time
from pathlib import Path

import pandas as pd
import pytest
from fastapi.testclient import TestClient

from api.app import create_app
from src import public_market_readonly as m

REQ = {"mode":"real-readonly-dry-run","provider":"akshare-public-market","market":"cn-a","instrumentType":"stock","symbol":"600519","humanApproved":True,"readOnly":True,"allowAccountRead":