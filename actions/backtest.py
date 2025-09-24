# actions/backtest.py
import sys, json, subprocess, pathlib, pandas as pd, dearpygui.dearpygui as dpg
from state import AppState
from ui.statusbar import add_text_status
from STRATEGIES.strategy_pt import simple_strategy, confluence_based_strategy
from ui.charts import generate_chart

def backtest_strategy(state: AppState, strategy_name: str):
    if state.csv_data is None or state.csv_path is None:
        add_text_status(state, "No CSV loaded for backtesting.")
        return

    script_path = pathlib.Path("clean_up\strats.py")
    if not script_path.exists():
        # Fallback: your uploaded script sits at project root
        script_path = pathlib.Path("clean_up\strats.py")

    proc = subprocess.Popen(
        [sys.executable, str(script_path)],
        stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
    )
    payload = json.dumps({"csv_path": str(state.csv_path)})
    stdout_data, stderr_data = proc.communicate(payload)

    if proc.returncode != 0:
        add_text_status(state, f"Strategy error: {stderr_data or stdout_data}")
        return

    add_text_status(state, f"stdout received from strategy: {stdout_data}")
    try:
        results = json.loads(stdout_data)
        add_text_status(state, f"Backtest Results: {results}")
    except Exception as e:
        add_text_status(state, f"Failed to parse strategy output: {e}")
    if strategy_name == "Simple Strategy":
        simple_strategy(state)
    elif strategy_name == "Confluence Based Strategy":
        confluence_based_strategy(state)
    elif strategy_name == "Please Select":
        add_text_status(state, "Please select a valid strategy.")
        return
    else:
        add_text_status(state, "Error")
        return
    

    # If main chart is not shown then show the main chart

    if not dpg.is_item_shown("chart"):
        generate_chart(state)


    equity_plot(state)

def equity_plot(state: AppState):
    try:
        df = pd.read_csv("sp500.csv")
    except Exception as e:
        add_text_status(state, f"No S&P 500 data: {e}")
        return

    df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
    df = df.dropna(subset=["Date", "Return_%"])

    # Remove any previous series
    if dpg.does_item_exist("equity_series"):
        dpg.delete_item("equity_series")
    if dpg.does_item_exist("backtest_equity_series"):
        dpg.delete_item("backtest_equity_series")

    # --- S&P 500 line: ensure float lists ---
    x = ((df["Date"].astype("int64") / 1e9).astype(float)).tolist()
    y = (df["Return_%"].astype(float)).tolist()

    dpg.show_item("equity_plot")
    dpg.add_line_series(
        x, y,
        parent="y_axis_equity",
        tag="equity_series",
        label="S&P 500 %", 
        skip_nan=True
    )

    # --- Backtest line: ensure float lists ---
    if state.backtest_results is not None and not state.backtest_results.empty:
        br = state.backtest_results.dropna(subset=["Date", "Cumulative Percentage Returns"]).copy()
        backtest_x = ((br["Date"].astype("int64") / 1e9).astype(float)).tolist()
        backtest_y = (br["Cumulative Percentage Returns"].astype(float)).tolist()

        # lengths must match
        n = min(len(backtest_x), len(backtest_y))
        backtest_x, backtest_y = backtest_x[:n], backtest_y[:n]

        dpg.add_line_series(
            backtest_x, backtest_y,
            parent="y_axis_equity",
            tag="backtest_equity_series",
            label=f'{dpg.get_value("strategy_combo")} Equity',
            skip_nan=True
        )

def reload_equity_plot(state: AppState):
    if not dpg.is_item_shown("equity_plot"):
        if dpg.does_item_exist("equity_series") or dpg.does_item_exist("backtest_equity_series"):
            dpg.show_item("equity_plot")
        else:
            add_text_status(state, "No equity curve loaded")
        
    



    
