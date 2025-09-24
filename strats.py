import sys
import json
import pandas as pd
from STRATEGIES.strategy_pt import simple_strategy
# Read the input JSON from stdin
try:
    input_data = json.load(sys.stdin)
    csv_path = input_data["csv_path"]
except Exception as e:
    print(json.dumps({"error": f"Failed to read input: {str(e)}"}))
    sys.exit(1)

# Load CSV
try:
    df = pd.read_csv(csv_path)
except Exception as e:
    print(json.dumps({"error": f"Failed to load CSV: {str(e)}"}))
    sys.exit(1)

# Run dummy backtest logic
try:
    result = {
        "row_count": len(df),
        "avg_close": df["Close"].mean() if "Close" in df.columns else None
    }

    # Output result to stdout
    json.dump(result, sys.stdout)

except Exception as e:
    print(json.dumps({"error": f"Failed during backtest logic: {str(e)}"}))
    sys.exit(1)
