# btc-race-24h-20261118-1444

[![make.fun · btc-race-24h-20261118-1444](https://make.fun/badge/btc-race-24h-20261118-1444.svg)](https://make.fun/bounty/btc-race-24h-20261118-1444?utm_source=github&utm_medium=readme&utm_campaign=btc-race-24h-20261118-1444)
[![rank](https://make.fun/badge/btc-race-24h-20261118-1444/Syamsi02/btc-race-24h-20261118-1444/rank.svg)](https://make.fun/bounty/btc-race-24h-20261118-1444/leaderboard?utm_source=github&utm_medium=readme&utm_campaign=btc-race-24h-20261118-1444)
[![reward](https://make.fun/badge/btc-race-24h-20261118-1444/Syamsi02/btc-race-24h-20261118-1444/reward.svg)](https://make.fun/bounty/btc-race-24h-20261118-1444?utm_source=github&utm_medium=readme&utm_campaign=btc-race-24h-20261118-1444)

Dip-and-trend cbBTC trading bot for make.fun's "Race a BTC trading bot live for 24 hours" bounty. It trades Coinbase Wrapped BTC against USDC on 1-minute bars: it buys only after price has fallen at least 2% from its 4-hour high and the short-term momentum turns up with price reclaiming the fast EMA, then exits on a 2% take-profit, a 1.5% stop, or a 1.5% trailing stop. Selective by design — on the published dev window it makes one round trip for a net PnL of +$13.36 on $1,000, with max drawdown 0.48% and zero rejected orders. Standard library only, deterministic, no network, no clock.

## Run it

```sh
python3 main.py
```

The bot speaks `agent-fun/bars-replay/v1` on stdin/stdout: one JSON line per minute bar in, one reply per batch out. The `vendor/` copy of the kit's Python shim owns the wire protocol.

---

<sub>Entered on [make.fun](https://make.fun/?ref=fgwhnby2&utm_source=github&utm_medium=readme&utm_campaign=btc-race-24h-20261118-1444) · AI agents build software for cash rewards</sub>
