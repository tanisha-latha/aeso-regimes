# aeso-regimes

When does Alberta's pool price follow gas, and when does it break away?

This project classifies every hour of the Alberta power market into a price
regime (gas-driven, wind-suppressed, scarcity spike, price floor) using public
AESO data, then tests how well supply conditions predict those regimes.

## Status

Early scaffold. Ingestion, features, regime rules, and the backtest are next.

## Question

Alberta is an energy-only market where gas-fired units often set the marginal
price, but wind output, planned outages, and tight supply regularly push the
pool price away from gas fundamentals. The goal is to quantify how often each
regime occurs, when it occurs (month and hour of day), and how much of the
price variance gas alone explains versus supply conditions.

## Data

- AESO public API: pool price, generation by fuel, wind and solar output,
  load, and outages. A free API key is available from the AESO developer
  portal.
- Alberta Energy monthly natural gas reference price, used as the gas
  benchmark.

## Limitations

The free gas benchmark is monthly, so this project does not compute an hourly
spark spread or implied heat rate. Regimes are defined from supply conditions
and price behaviour rather than an exact marginal-cost calculation.

## Plan

1. Ingest hourly data into SQLite incrementally.
2. Build features: gas-fired share, wind output, load, outage capacity.
3. Label regimes with transparent rules before trying any model.
4. Backtest a spike-prediction model and report where it fails.
5. Publish a static heatmap view of regimes by month and hour.

## Running it

```
pip install -e .
export AESO_API_KEY=your-key
python -m aeso_regimes.ingest
```
