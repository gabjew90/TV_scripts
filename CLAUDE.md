# What this project is

A TradingView Pine Script v6 indicator for discretionary + alert-driven leveraged crypto perpetual futures trading on the 1h–1D timeframes. It detects overbought/oversold overshoots and fires mean-reversion fade signals — but only when a regime classifier says reversion (not continuation) is the favored outcome.

# Development tooling

Pine Script development is done through the **TradingView MCP** (https://github.com/tradesdontlie/tradingview-mcp), which drives a live TradingView Desktop chart. Use it instead of editing `.pine` files blind.

Core workflow:
- `mcp__tradingview__pine_set_source` — inject script source into the editor
- `mcp__tradingview__pine_smart_compile` — compile and surface errors
- `mcp__tradingview__pine_get_errors` / `pine_get_console` — read compile errors and log output
- `mcp__tradingview__chart_set_symbol` / `chart_set_timeframe` — switch ticker/resolution for testing
- `mcp__tradingview__data_get_study_values` / `data_get_pine_labels` / `data_get_pine_lines` — read indicator output back off the chart to verify behavior
- `mcp__tradingview__capture_screenshot` — visually confirm signals
- `mcp__tradingview__replay_*` — backtest signal behavior bar-by-bar via chart replay

Note: `pine_get_source` can return 200KB+ on complex scripts — avoid unless editing.
