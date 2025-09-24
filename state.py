# state.py
from dataclasses import dataclass, field
from pathlib import Path
import pandas as pd
from typing import Optional

@dataclass
class AppState:
    csv_path: Optional[Path] = None
    csv_data: Optional[pd.DataFrame] = None
    sp500_data: Optional[pd.DataFrame] = None
    selected_interval: str = ""
    status_height: int = 200
    ui_ready: bool = False

    


    # Additions for backtesting DATA

    backtest_csv: Optional[Path] = None
    backtest_results: Optional[pd.DataFrame] = None
    backtest_results_list = []


    # Indicators

    ema_data_values: Optional[pd.Series] = None
    ema_period: int = 200
    
