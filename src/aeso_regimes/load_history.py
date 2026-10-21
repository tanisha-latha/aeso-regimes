"""Load AESO's historical hourly metered volumes, pool price and AIL files.

Source: "Hourly Metered Volumes and Pool Price and AIL data 2001 to July 2025"
on the AESO data requests page. Download the CSVs into data/raw/ and run:

    python -m aeso_regimes.load_history

The files are wide (one column per generating asset). This writes two tables:

    market      one row per hour: pool price, AIL, hour-ahead forecast,
                imports and exports by intertie
    asset_gen   long format: hour, asset id, metered MWh (blank cells dropped)
"""

import argparse
import sqlite3
from pathlib import Path

import pandas as pd

RAW_DIR = Path("data/raw")
DB_PATH = Path("data/aeso.db")
FILE_GLOB = "Hourly_Metered_Volumes_and_Pool_Price_and_AIL_*.csv"

TIME_COLS = ["Date_Begin_GMT", "Date_Begin_Local"]
MARKET_COLS = {
    "ACTUAL_POOL_PRICE": "pool_price",
    "ACTUAL_AIL": "ail_mw",
    "HOUR_AHEAD_POOL_PRICE_FORECAST": "hour_ahead_forecast",
    "EXPORT_BC": "export_bc",
    "EXPORT_MT": "export_mt",
    "EXPORT_SK": "export_sk",
    "IMPORT_BC": "import_bc",
    "IMPORT_MT": "import_mt",
    "IMPORT_SK": "import_sk",
}


def parse_times(s: pd.Series) -> pd.Series:
    # files mix "2001-01-01 7:00" and "1/1/2010 7:00"
    return pd.to_datetime(s, format="mixed").dt.strftime("%Y-%m-%d %H:%M")


def init_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(
        f"""
        CREATE TABLE IF NOT EXISTS market (
            hour_utc TEXT PRIMARY KEY,
            hour_local TEXT NOT NULL,
            {", ".join(f"{c} REAL" for c in MARKET_COLS.values())}
        );
        CREATE TABLE IF NOT EXISTS asset_gen (
            hour_utc TEXT NOT NULL,
            asset_id TEXT NOT NULL,
            mwh REAL NOT NULL,
            PRIMARY KEY (hour_utc, asset_id)
        ) WITHOUT ROWID;
        """
    )


def load_file(conn: sqlite3.Connection, path: Path, chunksize: int = 20_000) -> tuple[int, int]:
    n_market = n_gen = 0
    for chunk in pd.read_csv(path, chunksize=chunksize, encoding="utf-8-sig", low_memory=False):
        hour_utc = parse_times(chunk["Date_Begin_GMT"])

        market = pd.DataFrame({"hour_utc": hour_utc, "hour_local": parse_times(chunk["Date_Begin_Local"])})
        for src, dst in MARKET_COLS.items():
            market[dst] = pd.to_numeric(chunk[src], errors="coerce") if src in chunk else None

        asset_cols = [c for c in chunk.columns if c not in MARKET_COLS and c not in TIME_COLS
                      and not c.startswith("Unnamed")]
        gen = chunk[asset_cols].copy().assign(hour_utc=hour_utc).melt(
            id_vars="hour_utc", var_name="asset_id", value_name="mwh")
        gen["mwh"] = pd.to_numeric(gen["mwh"], errors="coerce")
        gen = gen.dropna(subset=["mwh"])

        conn.executemany(
            f"INSERT OR REPLACE INTO market VALUES ({', '.join('?' * len(market.columns))})",
            market.itertuples(index=False, name=None),
        )
        conn.executemany(
            "INSERT OR REPLACE INTO asset_gen VALUES (?, ?, ?)",
            gen[["hour_utc", "asset_id", "mwh"]].itertuples(index=False, name=None),
        )
        n_market += len(market)
        n_gen += len(gen)
    conn.commit()
    return n_market, n_gen


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--raw-dir", type=Path, default=RAW_DIR)
    ap.add_argument("--db", type=Path, default=DB_PATH)
    args = ap.parse_args()

    files = sorted(args.raw_dir.glob(FILE_GLOB))
    if not files:
        raise SystemExit(f"no files matching {FILE_GLOB} in {args.raw_dir}")

    args.db.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(args.db)
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("PRAGMA synchronous = OFF")
    init_schema(conn)
    for path in files:
        n_market, n_gen = load_file(conn, path)
        print(f"{path.name}: {n_market:,} hours, {n_gen:,} asset-hours")
    conn.close()


if __name__ == "__main__":
    main()
