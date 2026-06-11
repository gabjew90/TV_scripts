"""v0.4.6 feed verification: library OI vs ccxt; funding sign vs ccxt.
Reads the LIVE values printed by the chart Data Window (passed on the CLI,
harvested via data_get_study_values) and compares against Binance via ccxt.
Note: the chart's DW funding rate is in PERCENT (0.010 = 0.01%); ccxt returns
a decimal (0.0001) - only the SIGN is compared.
Usage: python feed_check_v046.py BTC/USDT:USDT --oi 78123.4 --fr 0.0001
"""
import argparse
import ccxt

ap = argparse.ArgumentParser()
ap.add_argument("market")            # e.g. BTC/USDT:USDT
ap.add_argument("--oi", type=float, required=True)   # DW open interest
ap.add_argument("--fr", type=float, required=True)   # DW funding rate
args = ap.parse_args()

ex = ccxt.binanceusdm()
oi = ex.fetch_open_interest(args.market)
fr = ex.fetch_funding_rate(args.market)
oi_ex = float(oi["openInterestAmount"])
fr_ex = float(fr["fundingRate"])
oi_ok = abs(args.oi - oi_ex) / oi_ex < 0.05          # 5% slack: feed sampling lag
fr_ok = (args.fr >= 0) == (fr_ex >= 0)               # sign agreement
print(f"OI  chart={args.oi:.1f} ccxt={oi_ex:.1f} -> {'OK' if oi_ok else 'MISMATCH'}")
print(f"FR  chart={args.fr:.6g} ccxt={fr_ex:.6g} -> {'OK (sign)' if fr_ok else 'SIGN MISMATCH'}")
raise SystemExit(0 if (oi_ok and fr_ok) else 1)
