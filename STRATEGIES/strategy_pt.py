import pandas as pd
from state import AppState
from ui.statusbar import add_text_status, add_text_status_backtest
import time as t
import dearpygui.dearpygui as dpg 



def simple_strategy(state: AppState):

    # Load CSV data (eth), using uploaded data 1
    # Ensure it is loaded into pandas
    # Perform simple algo on it
    # output results into a seperate CSV file using pandas
    # pass it through into UI -> table and chart
    # eventually incorporate everything into UI incliding variabnles

    # ----- 1 -----
    try:
        if state.csv_data is None:
            add_text_status(state, "No CSV data loaded for strategy.")
            return
        # Should already be in a dataframe
        backtest_data = state.csv_data
        add_text_status(state, "Backtesting working...")
    
    except Exception as e:
        add_text_status(state, f"Error loading CSV data: {e}")
        return
    # ----- 1 -----


    # ----- 2 -----
    # Perform a simple strategy
    # Define necessary colums in seperate variables
    open_col = backtest_data["Open"]
    close_col = backtest_data["Close"]
    # Date should not need to be reformatted via pandas into datetime
    date_col = backtest_data["Date"]

    # Check length of CSV data
    length = len(backtest_data) # On test data -> 2880
    add_text_status(state, f"CSV data length: {length}")
    add_text_status(state, "Performing simple strategy...")

    # Set up paper trading variables

    account_balance: float = 100000.0 # Starting balance
    trade_size: float = 1000.0 # Amount to risk per trade
    leverage: float = 10.0 # Leverage factor
    position: bool = False # Whether we are in a position
    bullish: bool = False # Whether the last candle was bullish

    # Create arrays for new dataframe 
    # They must synergise
    cumulative_percentage_returns = []
    account_balance_array = []
    time = []
    short_long = []


    # Count-controlled loop
    count = 0
    max_count = length # adjust as needed
    while count < max_count:
        # Strategy logic here:
        # Check whether bullish or bearish candle
        # If bullish, buy and hold for one candle
        # Vice versa for bearish
        # Risk 1000 dollars at 10x leverage
        if position == False:
            # Open Position
            position = True
            # Determine if bullish or bearish
            if open_col[count] - close_col[count] < 0:
                # Bullish candle
                bullish = True
                short_long.append("Long")
            else:
                bullish = False
                short_long.append("Short")

            # Add one to count
            count += 1


        else:
            # Close position
            position = False
            # Complete the one candle trade
            # Calcualte the percentage movement
            # Calculate position size and CHECK if there is enough balance to complete the trade
            # Append everything to the arrays 
            if bullish == True:
                # Bullish candle logic
                percentage_movement = (close_col[count] - open_col[count]) / open_col[count] * 100
                if account_balance >= (trade_size):
                    account_balance += (trade_size * leverage) * (percentage_movement / 100)
                    time.append(date_col[count])
                    percentage_change = (account_balance - 100000.0) / 100000.0 * 100
                    cumulative_percentage_returns.append(percentage_change)
                    account_balance_array.append(account_balance)

                    # Add text status for successful trade alongside data
                    add_text_status_backtest(state, f"Trade successful: {short_long[-1]} on {date_col[count]} | New Balance: {account_balance:.2f} | Percentage Change: {percentage_change:.2f}%")

                
                else:
                    add_text_status_backtest(state, "Not enough balance to complete trade.")
                    break

            
            else:
                # Bearish candle logic
                percentage_movement = 0 - ((close_col[count] - open_col[count]) / open_col[count] * 100)
                if account_balance >= (trade_size):
                    account_balance += (trade_size * leverage) * (percentage_movement / 100)
                    time.append(date_col[count])
                    percentage_change = (account_balance - 100000.0) / 100000.0 * 100
                    cumulative_percentage_returns.append(percentage_change)
                    account_balance_array.append(account_balance)

                    # Add text status for successful trade alongside data
                    add_text_status_backtest(state, f"Trade successful: {short_long[-1]} on {date_col[count]} | New Balance: {account_balance:.2f} | Percentage Change: {percentage_change:.2f}%")

            # Add one to count
            count += 1
    

    t.sleep(1) # Allow time for UI to update

    add_text_status_backtest(state, "Strategy completed.")
    add_text_status_backtest(state, f"Final account balance: {account_balance:.2f}")

    final_data = {
        "Date": time,
        "Cumulative Percentage Returns": cumulative_percentage_returns,
        "Account Balance": account_balance_array,
        "Short/Long": short_long
    }

    final_results_df = pd.DataFrame(final_data)
    final_results_df["Date"] = pd.to_datetime(final_results_df["Date"], errors="coerce")
    state.backtest_results = final_results_df


def confluence_based_strategy(state: AppState):
    # ---------- 0) Load & validate ----------
    try:
        if state.csv_data is None:
            add_text_status(state, "There is no CSV loaded currently.")
            return
        trading_data = state.csv_data
    except Exception as e:
        add_text_status(state, f"Error: {e}")
        return

    # column safety (support either 'Date' or 'Time')
    time_col_name = "Date" if "Date" in trading_data.columns else ("Time" if "Time" in trading_data.columns else None)
    if time_col_name is None:
        add_text_status(state, "CSV must include a 'Date' or 'Time' column.")
        return

    # required OHLC columns
    for c in ["Open", "High", "Low", "Close"]:
        if c not in trading_data.columns:
            add_text_status(state, f"CSV is missing required column: {c}")
            return

    # ---------- 1) Extract series ----------
    df_open  = trading_data["Open"].reset_index(drop=True)
    df_high  = trading_data["High"].reset_index(drop=True)
    df_low   = trading_data["Low"].reset_index(drop=True)
    df_close = trading_data["Close"].reset_index(drop=True)
    df_time  = pd.to_datetime(trading_data[time_col_name], errors="coerce").reset_index(drop=True)

    length: int = len(trading_data)
    add_text_status(state, f"CSV data length: {length}")
    add_text_status(state, "Performing confluence-based strategy...")

    # ---------- 2) Params ----------
    leverage: float = 10.0
    starting_balance: float = 100000.0
    trade_risk_cash: float = 1000.0   # risk per trade (cash, not %)
    ema_period: int = 200

    if length < ema_period + 3:
        add_text_status(state, f"Not enough rows for EMA({ema_period}) and pattern detection.")
        return

    # ---------- 3) Compute EMA (use pandas ewm for correctness) ----------
    ema = df_close.ewm(span=ema_period, adjust=False).mean()

    # ---------- 4) State & outputs ----------
    position_open: bool = False
    trend_bull: bool = False   # True when looking for bullish setup (price below EMA), False for bearish
    pct_gap_ok: bool = False   # true if price is >= 1% away from EMA in the trend direction

    # outputs
    side_array = []                 # "Long"/"Short"
    balance_array = []              # account balance after each closed trade
    time_array = []                 # time of trade close
    cum_pct_array = []              # cumulative % vs starting_balance

    balance = starting_balance

    # ---------- 5) Helpers ----------
    def pct_away_below(price, ema_val) -> float:
        # price below ema; positive % if at least 1% below
        return (ema_val / price - 1.0) * 100.0

    def pct_away_above(price, ema_val) -> float:
        # price above ema; positive % if at least 1% above
        return (price / ema_val - 1.0) * 100.0

    # Risk/Reward 1:2 helper: compute PnL given entry and exit prices and direction
    def pnl_cash(entry, exit_, side):
        pct_move = (exit_ / entry - 1.0) * (100.0 if side == "Long" else -100.0)
        return (trade_risk_cash * leverage) * (pct_move / 100.0)

    # ---------- 6) Scan ----------
    i = ema_period  # start after EMA is meaningful
    # we need lookahead of 2 candles for the 3-candle formation
    while i < length - 2:

        price = df_close.iloc[i]
        ema_now = ema.iloc[i]

        if not position_open:
            # Decide trend context & 1% distance from EMA
            if price < ema_now:
                trend_bull = True
                pct_gap_ok = pct_away_below(price, ema_now) >= 1.0
            else:
                trend_bull = False
                pct_gap_ok = pct_away_above(price, ema_now) >= 1.0

            if not pct_gap_ok:
                i += 1
                continue

            # Look for 3-candle formation in direction of trend
            c0_o, c0_h, c0_l, c0_c = df_open.iloc[i],   df_high.iloc[i],   df_low.iloc[i],   df_close.iloc[i]
            c1_o, c1_h, c1_l, c1_c = df_open.iloc[i+1], df_high.iloc[i+1], df_low.iloc[i+1], df_close.iloc[i+1]
            c2_o, c2_h, c2_l, c2_c = df_open.iloc[i+2], df_high.iloc[i+2], df_low.iloc[i+2], df_close.iloc[i+2]

            if trend_bull:
                # Need three bullish candles
                if (c0_c > c0_o) and (c1_c > c1_o) and (c2_c > c2_o):
                    # Bullish FVG: first high < third low
                    if c0_h < c2_l:
                        add_text_status_backtest(state, "BULLISH FVG FOUND")
                        # Define FVG bounds
                        fvg_low  = c0_h   # bottom of the gap
                        fvg_high = c2_l   # top of the gap

                        # Search forward for either: (a) EMA violation (price closes above EMA → cancel)
                        # or (b) retrace into FVG and then close back above fvg_high → enter long
                        j = i + 3
                        entered = False
                        while j < length:
                            # cancel if price flips context (closes above EMA before entry)
                            if df_close.iloc[j] > ema.iloc[j]:
                                # still okay for bull; crossing ABOVE EMA is actually fine for bulls
                                # but we only cancel if it *crosses below* EMA before entry (anti-trend)
                                pass

                            # For bulls we invalidate if we CLOSE *below* EMA while preparing? No; initial context is below EMA.
                            # Keep it simple: do not invalidate on EMA during setup; we’ll invalidate only if FVG breaks.
                            # Check retrace into FVG
                            if fvg_low < df_close.iloc[j] < fvg_high:
                                # Wait for close back above fvg_high to confirm continuation
                                k = j + 1
                                invalid = False
                                while k < length:
                                    # Invalidate setup if candle closes below fvg_low (gap broken)
                                    if df_close.iloc[k] <= fvg_low:
                                        invalid = True
                                        break
                                    if df_close.iloc[k] >= fvg_high:
                                        # Enter long at close of this confirming candle
                                        entry_idx = k
                                        entry_px  = df_close.iloc[entry_idx]
                                        side      = "Long"
                                        # SL at fvg_low, TP at RR 1:2
                                        stop_px = fvg_low
                                        risk_perc = (entry_px - stop_px) / entry_px * 100.0
                                        if risk_perc <= 0:
                                            invalid = True
                                            break
                                        tp_px = entry_px * (1 + 2 * ((entry_px - stop_px) / entry_px))
                                        # Manage trade forward
                                        m = entry_idx + 1
                                        exit_px = None
                                        exit_time = None
                                        while m < length:
                                            hi = df_high.iloc[m]
                                            lo = df_low.iloc[m]
                                            # Hit TP?
                                            if hi >= tp_px:
                                                exit_px = tp_px
                                                exit_time = df_time.iloc[m]
                                                break
                                            # Hit SL?
                                            if lo <= stop_px:
                                                exit_px = stop_px
                                                exit_time = df_time.iloc[m]
                                                break
                                            m += 1
                                        if exit_px is None:
                                            # Close at last close
                                            exit_px = df_close.iloc[length - 1]
                                            exit_time = df_time.iloc[length - 1]
                                        # Update P&L
                                        pnl = pnl_cash(entry_px, exit_px, side)
                                        if balance >= trade_risk_cash:
                                            balance += pnl
                                            time_array.append(exit_time)
                                            side_array.append(side)
                                            balance_array.append(balance)
                                            cum_pct_array.append((balance - starting_balance) / starting_balance * 100.0)
                                            add_text_status_backtest(
                                                state,
                                                f"Trade {side} closed @ {exit_time} | Δ: {pnl:+.2f} | Bal: {balance:.2f}"
                                            )
                                        else:
                                            add_text_status_backtest(state, "Not enough balance to take trade.")
                                        entered = True
                                        break
                                    k += 1
                                # end while k
                                if invalid or entered:
                                    break
                            # advance j
                            j += 1
                        # end while j
                        i = max(i + 1, j if 'j' in locals() else i + 1)
                        continue
            else:
                # Bearish trend: three bearish candles
                if (c0_c < c0_o) and (c1_c < c1_o) and (c2_c < c2_o):
                    # Bearish FVG: first low > third high
                    if c0_l > c2_h:
                        add_text_status_backtest(state, "BEARISH FVG FOUND")
                        fvg_high = c0_l  # top of gap
                        fvg_low  = c2_h  # bottom of gap

                        j = i + 3
                        entered = False
                        while j < length:
                            # Check retrace into FVG
                            if fvg_low < df_close.iloc[j] < fvg_high:
                                # Wait for close back below fvg_low to confirm continuation
                                k = j + 1
                                invalid = False
                                while k < length:
                                    # Invalidate if candle closes above fvg_high
                                    if df_close.iloc[k] >= fvg_high:
                                        invalid = True
                                        break
                                    if df_close.iloc[k] <= fvg_low:
                                        # Enter short at close of this confirming candle
                                        entry_idx = k
                                        entry_px  = df_close.iloc[entry_idx]
                                        side      = "Short"
                                        # SL at fvg_high, TP at RR 1:2
                                        stop_px = fvg_high
                                        risk_perc = (stop_px - entry_px) / entry_px * 100.0
                                        if risk_perc <= 0:
                                            invalid = True
                                            break
                                        tp_px = entry_px * (1 - 2 * ((stop_px - entry_px) / entry_px))
                                        # Manage trade forward
                                        m = entry_idx + 1
                                        exit_px = None
                                        exit_time = None
                                        while m < length:
                                            hi = df_high.iloc[m]
                                            lo = df_low.iloc[m]
                                            # Hit TP?
                                            if lo <= tp_px:
                                                exit_px = tp_px
                                                exit_time = df_time.iloc[m]
                                                break
                                            # Hit SL?
                                            if hi >= stop_px:
                                                exit_px = stop_px
                                                exit_time = df_time.iloc[m]
                                                break
                                            m += 1
                                        if exit_px is None:
                                            exit_px = df_close.iloc[length - 1]
                                            exit_time = df_time.iloc[length - 1]
                                        pnl = pnl_cash(entry_px, exit_px, side)
                                        if balance >= trade_risk_cash:
                                            balance += pnl
                                            time_array.append(exit_time)
                                            side_array.append(side)
                                            balance_array.append(balance)
                                            cum_pct_array.append((balance - starting_balance) / starting_balance * 100.0)
                                            add_text_status_backtest(
                                                state,
                                                f"Trade {side} closed @ {exit_time} | Δ: {pnl:+.2f} | Bal: {balance:.2f}"
                                            )
                                        else:
                                            add_text_status_backtest(state, "Not enough balance to take trade.")
                                        entered = True
                                        break
                                    k += 1
                                if invalid or entered:
                                    break
                            j += 1
                        i = max(i + 1, j if 'j' in locals() else i + 1)
                        continue

        # advance scanner when nothing else triggered
        i += 1

    # ---------- 7) Finalize ----------
    if len(time_array) == 0:
        add_text_status_backtest(state, "No qualifying trades found.")
    else:
        add_text_status_backtest(state, f"Strategy completed. Final balance: {balance:.2f}")

    results = pd.DataFrame({
        "Date": time_array,
        "Cumulative Percentage Returns": cum_pct_array,
        "Account Balance": balance_array,
        "Short/Long": side_array
    })
    results["Date"] = pd.to_datetime(results["Date"], errors="coerce")
    state.backtest_results = results


            




            










    






                






