"""Reversal + trend cbBTC bot for make.fun btc-race-24h-20261118-1444.

Strategy (fresh design, standard library only, deterministic):
- Reversal sleeve: after price has fallen REV_DROP below its 240-bar high,
  buy only once the short-term momentum turns up and price reclaims the fast
  EMA. Exits on take-profit, stop, trailing stop, or loss of the fast EMA.
- Trend sleeve: slow EMA crossover rides multi-hour legs.
- Mean-reversion sleeve: buy Bollinger lower-band touches, exit at the band
  middle. Dip sleeve: buy oversold dips below the slow EMA.
- Every position carries a stop, a trailing stop and a take-profit, plus a
  short cooldown after each exit so the bot does not churn on whipsaws.
- Position sizes are fractions of equity, capped by the harness weight room.
- No clock, no environment, no randomness: two runs on the same bars produce
  the same orders.
"""

import math
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "vendor"))
import makefun_bars

SYMBOL = "CBBTC"

FAST = 12
SLOW = 120
RSI_LEN = 14
MOM_LEN = 30
BB_LEN = 60
BB_K = 2.0
REV_LEN = 240
REV_MOM_LEN = 15

TREND_BUY_FRAC = 0.00
DIP_BUY_FRAC = 0.00
BB_BUY_FRAC = 0.00
REV_BUY_FRAC = 0.75
MOM_MIN = 0.001
REV_DROP = 0.02
REV_MOM_MIN = 0.0
DIP_DEV = 0.005
DIP_RSI = 35
STOP_PCT = 0.015
TRAIL_PCT = 0.015
TAKE_PCT = 0.02
COOLDOWN = 10
MAX_SLIP_BPS = 100
# Exit rule for the trend sleeve: "ema" = exit when EMA fast crosses below
# slow; "price" = exit when close falls below the slow EMA; "stops" = exit
# only on stop / trailing stop / take-profit.
EXIT_MODE = "stops"


class Bot:
    def __init__(self):
        self.closes = []
        self.highs = []
        self.ema_fast = None
        self.ema_slow = None
        self.gains = []
        self.losses = []
        self.entry_price = None
        self.peak = None
        self.mode = None
        self.cooldown_until = -1

    def _ema(self, prev, close, n):
        alpha = 2.0 / (n + 1)
        return close + alpha * (prev - close) if prev is not None else float(close)

    def _rsi(self):
        if len(self.gains) < RSI_LEN:
            return None
        avg_gain = sum(self.gains[-RSI_LEN:]) / RSI_LEN
        avg_loss = sum(self.losses[-RSI_LEN:]) / RSI_LEN
        if avg_loss == 0:
            return 100.0
        rs = avg_gain / avg_loss
        return 100.0 - 100.0 / (1.0 + rs)

    def _bb(self):
        if len(self.closes) < BB_LEN:
            return None, None
        window = self.closes[-BB_LEN:]
        mid = sum(window) / BB_LEN
        var = sum((x - mid) ** 2 for x in window) / BB_LEN
        return mid, math.sqrt(var)

    def on_batch(self, state, batch):
        if state.warming_up:
            return []
        close = state.close(SYMBOL)
        if close is None:
            return []
        close = float(close)

        if self.closes:
            change = close - self.closes[-1]
            self.gains.append(change if change > 0 else 0.0)
            self.losses.append(-change if change < 0 else 0.0)
        self.closes.append(close)
        self.highs.append(close)
        self.ema_fast = self._ema(self.ema_fast, close, FAST)
        self.ema_slow = self._ema(self.ema_slow, close, SLOW)

        if len(self.closes) < max(SLOW, BB_LEN, REV_LEN) + 5:
            return []

        held = state.positions.get(SYMBOL)
        qty = held.qty if held else 0
        mid, sd = self._bb()

        if qty > 0:
            if close > (self.peak or close):
                self.peak = close
            exit_now = False
            if self.mode == "dip" and close >= self.ema_slow:
                exit_now = True
            elif self.mode == "bb" and mid is not None and close >= mid:
                exit_now = True
            elif self.mode == "trend" and EXIT_MODE == "ema" and self.ema_fast < self.ema_slow:
                exit_now = True
            elif self.mode == "trend" and EXIT_MODE == "price" and close < self.ema_slow:
                exit_now = True
            elif self.entry_price is not None and close <= self.entry_price * (1.0 - STOP_PCT):
                exit_now = True
            elif self.peak is not None and close <= self.peak * (1.0 - TRAIL_PCT):
                exit_now = True
            elif self.entry_price is not None and close >= self.entry_price * (1.0 + TAKE_PCT):
                exit_now = True
            if exit_now:
                self.cooldown_until = state.seq + COOLDOWN
                self.entry_price = None
                self.peak = None
                self.mode = None
                return [{"side": "sell", "symbol": SYMBOL, "qty": qty,
                         "max_slippage_bps": MAX_SLIP_BPS}]
            return []

        if state.seq < self.cooldown_until:
            return []

        momentum = (close - self.closes[-MOM_LEN - 1]) / self.closes[-MOM_LEN - 1]
        rev_momentum = (close - self.closes[-REV_MOM_LEN - 1]) / self.closes[-REV_MOM_LEN - 1]
        rsi = self._rsi()
        hi240 = max(self.highs[-REV_LEN:])
        frac = None
        mode = None
        if (TREND_BUY_FRAC > 0 and self.ema_fast > self.ema_slow
                and close > self.ema_fast and momentum > MOM_MIN):
            frac = TREND_BUY_FRAC
            mode = "trend"
        elif (BB_BUY_FRAC > 0 and mid is not None and sd and sd > 0
                and close < mid - BB_K * sd):
            frac = BB_BUY_FRAC
            mode = "bb"
        elif (DIP_BUY_FRAC > 0 and rsi is not None and rsi < DIP_RSI
                and close < self.ema_slow * (1.0 - DIP_DEV)):
            frac = DIP_BUY_FRAC
            mode = "dip"
        elif (REV_BUY_FRAC > 0 and (hi240 - close) / hi240 >= REV_DROP
                and rev_momentum > REV_MOM_MIN and close > self.ema_fast):
            frac = REV_BUY_FRAC
            mode = "rev"
        if frac is None or frac <= 0:
            return []

        equity = state.equity
        spend = int(equity * frac)
        room = state.weight_room(SYMBOL)
        spend = min(spend, room, state.cash)
        min_notional = int(state.hello["fees"]["min_notional_quote_units"])
        if spend <= min_notional:
            return []
        self.entry_price = close
        self.peak = close
        self.mode = mode
        return [{"side": "buy", "symbol": SYMBOL,
                 "notional_quote_units": spend,
                 "max_slippage_bps": MAX_SLIP_BPS}]


def main():
    bot = Bot()
    makefun_bars.run(bot.on_batch)


if __name__ == "__main__":
    main()
