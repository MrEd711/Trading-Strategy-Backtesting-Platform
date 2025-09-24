# app.py
import threading
import dearpygui.dearpygui as dpg
from state import AppState
from ui.charts import (
    generate_chart, tooltip_loop, weight_slider_cb, crosshair_cb,
    configure_main_plot_cb, sync_on_zoom_cb, chart_fullsize, settings_window
)
from ui.statusbar import configure_status_bar_cb, add_text_status, bottom_status_backtest
from actions.dataflow import on_load_csv, file_dialog_download_cb
from actions.backtest import backtest_strategy, reload_equity_plot

def build_ui(state: AppState):
    dpg.create_context()
    dpg.create_viewport(title="Backtesting Program", width=1200, height=900)

    with dpg.value_registry():
        dpg.add_bool_value(tag="crosshair_value", default_value=False)
        dpg.add_bool_value(tag="auto_scroll_value", default_value=True)
        dpg.add_bool_value(tag="auto_scroll_value_backtest", default_value=True)

    # Main chart window (hidden initially)    
    # Create a button which toggles the chart fullscreen

    with dpg.window(label="CHART WINDOW", tag="chart", show=False, height=600, width=800):
        with dpg.child_window(border=True, label="ETH/USD CANDLESTICK CHART", width=-1, height=0.7, tag="child_window_candle"):
            with dpg.group(horizontal=True):
                dpg.add_slider_float(tag="ratio_change", default_value=0.7, min_value=0.2, max_value=0.9,
                                    callback=lambda *a: configure_main_plot_cb(), label="RATIO")
                dpg.add_button(label="Toggle Fullscreen", tag = "eth_chart_fullscreen", callback=lambda s, a: chart_fullsize(state, s, a)) # Why lambda s, a, an not just lambda
            with dpg.group(horizontal=True):
                dpg.add_slider_float(tag="weight_slider", min_value=0.1, max_value=3, default_value=0.5,
                                     callback=weight_slider_cb, label="Weight")
                # Add a button to open a settings window for crosshair and indicators
                dpg.add_button(label="Settings", callback=lambda s, a: settings_window(state, s, a)) # Create a seperate script
                
                #dpg.add_checkbox(label="Crosshair", tag="crosshair_checkbox", source="crosshair_value",
                                 #callback=lambda *a: crosshair_cb())
            with dpg.plot(label="ETH/USD", tag="plot", height=-1, width=-1, no_menus=True, crosshairs=False):
                dpg.add_plot_axis(dpg.mvXAxis, tag="x_axis", label="Date", scale=dpg.mvPlotScale_Time)
                dpg.add_plot_axis(dpg.mvYAxis, tag="y_axis", label="Price")
        with dpg.child_window(label="VOLUME", border=True, width=-1, height=0.3, tag="child_window_histo"):
            with dpg.plot(label="VOLUME", tag="volume_plot", height=-1, width=-1, no_menus=True, crosshairs=True):
                dpg.add_plot_axis(dpg.mvXAxis, label="DATE", tag="x_axis_volume", scale=dpg.mvPlotScale_Time)
                dpg.add_plot_axis(dpg.mvYAxis, label="VOLUME", tag="y_axis_volume")

    # Main chart settings window

    with dpg.window(label = "Chart Settings", tag = "chart_settings", show=False, width=300, height=200):
        with dpg.tree_node(label = "General Settings", default_open=True):
            dpg.add_checkbox(label="Crosshair", tag="crosshair_checkbox", source="crosshair_value",
                                 callback=lambda *a: crosshair_cb())
        with dpg.tree_node(label = "Indicators", default_open=False):
            dpg.add_text("Indicator settings will go here.")
            dpg.add_input_int(label="EMA Period", default_value=state.ema_period, tag="ema_period_input") # This will need to be edited when re-opened

        dpg.add_button(label="Save and Close", tag = "save_and_close", callback=lambda s, a: settings_window(state, s, a) # Will need to save the EMA period and other settings (put into seperate function)
                       )


    with dpg.item_handler_registry(tag="chart_resize"):
        dpg.add_item_resize_handler(callback=lambda *a: configure_main_plot_cb())
    dpg.bind_item_handler_registry("chart", "chart_resize")

    # File dialogs
    with dpg.file_dialog(directory_selector=False, show=False, callback=lambda s,a: on_load_csv(state, s, a),
                         tag="file_dialog_csv", cancel_callback=lambda s,a: None, width=700, height=400):
        dpg.add_file_extension(".csv", color=(0,255,0,255))

    with dpg.file_dialog(directory_selector=False, show=False,
                         callback=lambda s,a: file_dialog_download_cb(state, s, a),
                         tag="file_dialog_py", cancel_callback=lambda s,a: None, width=700, height=400):
        dpg.add_file_extension(".py", color=(0,255,0,255))

    # Data entry window
    with dpg.window(label="Data Enter", tag="data_entry", width=500, height=150, show=False):
        dpg.add_text("Errors will appear here.", tag="error_text")
        dpg.add_combo(("5m","15m","30m","1H","2H","4H","1D"), label="Select Interval", tag="interval_combo")
        dpg.add_input_text(label="Number of days needed:", tag="days_input")
        dpg.add_button(label="Re-download data", callback=lambda: dpg.show_item("file_dialog_py"))

    # Menu bar
    with dpg.viewport_menu_bar():
        with dpg.menu(label="BACKTESTING STRATEGY"):
            dpg.add_menu_item(label="BACKTEST", callback=lambda: dpg.show_item("backtest_config")) # EDIT
        with dpg.menu(label="CSV VIEWER"):
            dpg.add_menu_item(label="Load CSV", callback=lambda: dpg.show_item("file_dialog_csv"))
            dpg.add_menu_item(label="Generate Chart", callback=lambda: generate_chart(state))
        with dpg.menu(label="Download"):
            dpg.add_menu_item(label="Download Data", callback=lambda: dpg.show_item("data_entry"))
        dpg.add_menu_item(label="Status Bar", callback=lambda: (dpg.show_item("status_bar"), configure_status_bar_cb(state)))
        with dpg.menu(label="Settings"):
            dpg.add_menu_item(label="Show Metrics", callback=lambda: dpg.show_metrics())
            dpg.add_menu_item(label="Toggle Fullscreen", callback=lambda: (dpg.toggle_viewport_fullscreen(), configure_status_bar_cb(state)))
    

    # Backtesting window for selecting strategies and viewing results.



    with dpg.window(label= "Backtesting Config", tag = "backtest_config", show=False, width=500, height=300):
        # Create a child window for strategy selection
        with dpg.child_window(label = "Strategy Selection", tag = "strategy_selection", height = 200, width = -1):
            with dpg.group(horizontal=False):
                with dpg.group(horizontal = True):
                    dpg.add_combo(("Please Select", "Simple Strategy", "Confluence Based Strategy"), default_value="Please Select", tag="strategy_combo", label = "Strategy Selection", width = 150)
                with dpg.group(horizontal = True):
                    dpg.add_button(label= "Load CSV", callback = lambda: dpg.show_item("file_dialog_csv")) 
                    dpg.add_text(f"Current CSV: {str(state.csv_path)}", tag = "CSV_CURRENT") # ADD NECESSARY VARIABLE WHICH CHANGES WHEN CSV IS LOADED
                dpg.add_button(label = "Re-load equity plot", tag = "equity_plot_reload", callback = lambda: reload_equity_plot(state)) # ADD NECESSARY CALLBACK                                   
                dpg.add_text("")
                dpg.add_button(label= "Run Backtest", callback=lambda: backtest_strategy(state, str(dpg.get_value("strategy_combo")))) # ADD ARGUMENTS FOR THE SELECTED STRATEGY BASED OFF OF THE COMBO
                
        

        # Create a child window for another status bar for backtesting
        with dpg.group(horizontal = True):
            dpg.add_button(label = "Scroll to botton", tag = "status_backtest_bottom", callback=lambda: bottom_status_backtest(state)) # Add callback
            dpg.add_checkbox(label = "Auto Scroll", tag = "autoscroll_checkbox_bactest", source = "auto_scroll_value_backtest")
        with dpg.child_window(label = "Backtest Status", tag = "backtest_status", height = -1, width = -1):
            dpg.add_text("Backtest Status: Ready")
        # Create function for auto scroll and adding text to the status bar


    # Equity plot window
    with dpg.window(label="equity_plot", tag="equity_plot", show=False, width=800, height=600):
        with dpg.plot(label="Equity Plot", tag="equity_plot_graph", height=-1, width=-1, no_menus=True, crosshairs=True):
            dpg.add_plot_legend()
            dpg.add_plot_axis(dpg.mvXAxis, label="Date", tag="x_axis_equity", scale=dpg.mvPlotScale_Time)
            dpg.add_plot_axis(dpg.mvYAxis, label="Cumulative Percentage Returns", tag="y_axis_equity")


    # Status bar
    with dpg.window(label="Status bar", tag="status_bar", autosize=False, no_move=True, no_resize=True,
                    width=800, height=state.status_height, show=True):
        with dpg.group(horizontal=True):
            dpg.add_checkbox(label="auto_scroll", tag="autoscroll", source="auto_scroll_value")
        with dpg.child_window(tag="status_child"):
            dpg.add_text("Ready")

    dpg.set_viewport_resize_callback(lambda: configure_status_bar_cb(state))

    dpg.setup_dearpygui()
    dpg.show_viewport()
    state.ui_ready = True

    # Tooltip thread (daemon)
    t = threading.Thread(target=tooltip_loop, args=(state,), daemon=True)
    t.start()

def run_event_loop():
    while dpg.is_dearpygui_running():
        if dpg.is_item_shown("chart"):
            if dpg.does_item_exist("x_axis") and dpg.does_item_exist("x_axis_volume"):
                x_min, x_max = dpg.get_axis_limits("x_axis")
                dpg.set_axis_limits("x_axis_volume", x_min, x_max)
        dpg.render_dearpygui_frame()
    dpg.destroy_context()

if __name__ == "__main__":
    state = AppState()
    build_ui(state)
    run_event_loop()
