TLT CLOUD DATABASE EXTRACTOR

This creates a much smaller SQLite database for Streamlit Cloud.

SOURCE
C:\MarketVector\Database\ibkr_market_data.sqlite

OUTPUT
data\streamlit_market_data.sqlite

WHAT IT COPIES
- relationship_bars_day only for symbols actually needed by the dashboards
- 8 years of OHLC history by default
- Daily output tables
- Weekly output tables

DAILY TABLES
- tlt_expected_moves_day
- tlt_movement_leadlag_day
- tlt_movement_events_day

WEEKLY TABLES
- tlt_expected_moves_week
- tlt_movement_leadlag_week
- tlt_movement_events_week

HOW TO RUN
Double-click:
BUILD_CLOUD_DATABASE.bat

Or:
python build_cloud_database.py --source "C:\MarketVector\Database\ibkr_market_data.sqlite" --output "data\streamlit_market_data.sqlite" --daily --weekly --history-years 8

THEN PUSH TO GITHUB
git lfs install
git lfs track "*.sqlite"
git add .gitattributes
git add .
git commit -m "Add slim cloud database"
git push

VERIFY
git lfs ls-files

You should see:
data/streamlit_market_data.sqlite

To make it even smaller, use:
--history-years 5
