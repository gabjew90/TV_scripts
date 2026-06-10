"""v0.4 Task-4 OI cross-check (sanity, not parity - spec section 8 reason 3:
OI feeds sample differently; OI never gates, so feed noise is tolerable and
measured).

Pine harvest (BTC 4H, v0.4.0) reported setup-window OI deltas:
  T1 ENT S @1780963200: oi_d = -4.24%  (window start ~1780732800, tl-seed bar)
  T1 ARM S @1780977600: oi_d = -4.50%  (same oi0 reference)
  T1 SKP S @1781006400: oi_d = -2.45%

Check: Binance USDT-M openInterestHistory at the same 4h timestamps should
show the SAME SIGN and roughly similar magnitude of change from the window
start. Pass = sign agreement on all rows; magnitudes reported for the record.
"""
import ccxt

EX = ccxt.binanceusdm()
ROWS = EX.fetch_open_interest_history("BTC/USDT:USDT", "4h", limit=120)
oi_by_ts = {int(r["timestamp"] / 1000): float(r["info"]["sumOpenInterest"]) for r in ROWS}

REF = 1780732800   # Pine oi0 reference bar (tl-seed after the 1780718400 reset)
CASES = [(1780963200, -4.24), (1780977600, -4.50), (1781006400, -2.45)]

missing = [t for t in [REF] + [c[0] for c in CASES] if t not in oi_by_ts]
if missing:
    print("bars missing from exchange OI history (30d API limit?):", missing)
    raise SystemExit(1)

oi0 = oi_by_ts[REF]
fails = 0
print(f"exchange OI @ref {REF}: {oi0:.0f}")
for t, pine_d in CASES:
    ex_d = 100.0 * (oi_by_ts[t] - oi0) / oi0
    sign_ok = (ex_d < 0) == (pine_d < 0)
    print(f"  {t}: exchange {ex_d:+.2f}%  vs pine {pine_d:+.2f}%  -> {'SIGN OK' if sign_ok else 'SIGN MISMATCH'}")
    if not sign_ok:
        fails += 1
raise SystemExit(1 if fails else 0)
