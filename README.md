# TLT Daily Actionable Trade Dashboard

This is the GitHub + Streamlit Community Cloud deployment package.

## Latest Daily features included

- 0-15 trading-day follower windows
- TLT hold/reversal logic
- Mid/Extended-lag stock-specific reversal logic
- 200-day SMA distance
- Overextended stocks hidden by default with toggle to show
- MA200 Entry column hidden
- Weekly resistance target
- Potential upside percentage

---

## 1. Build the slim cloud database

Double-click:

`BUILD_CLOUD_DATABASE.bat`

It reads:

`C:\MarketVector\Database\ibkr_market_data.sqlite`

and creates:

`data\streamlit_market_data.sqlite`

The extractor copies only the symbols and tables required by this dashboard, plus the historical OHLC data required by the Daily forecasting logic.

---

## 2. Daily one-click workflow

For normal daily operation:

1. Update the core market database.
2. Double-click `BUILD_AND_PUSH_DAILY.bat`.
3. The slim cloud database is rebuilt.
4. Relevant deployment files are staged.
5. Local changes are committed.
6. The latest GitHub changes are pulled/rebased.
7. The commit is pushed to `main`.
8. Streamlit Community Cloud should redeploy automatically.

The order is intentionally:

`BUILD -> STAGE -> COMMIT -> PULL/REBASE -> PUSH`

This avoids the `cannot pull with rebase: You have unstaged changes` error.

---

## 3. Files included in the normal GitHub push

The daily update script stages these files when present:

- `app.py`
- `app_actionable.py`
- `actionable_engine.py`
- `db.py`
- `config.yaml`
- `requirements.txt`
- `runtime.txt`
- `build_cloud_database.py`
- `BUILD_CLOUD_DATABASE.bat`
- `DAILY_GITHUB_UPDATE.bat`
- `BUILD_AND_PUSH_DAILY.bat`
- `README.md`
- `.gitignore`
- `.gitattributes`
- `data\streamlit_market_data.sqlite`

The script does not use `git add .`, which reduces the risk of accidentally uploading backups, logs, caches, unrelated databases, ZIP files, or temporary files.

---

## 4. Git LFS

The cloud SQLite database should be managed through Git LFS.

One-time setup from the project root:

```bash
git lfs install
git lfs track "*.sqlite"
git add .gitattributes
git commit -m "Configure Git LFS"
```

Verify:

```bash
git lfs ls-files
```

You should see:

`data/streamlit_market_data.sqlite`

Do not run `git lfs track "*.sqlite"` as part of the normal daily workflow. It only needs to be configured once.

---

## 5. GitHub

Repository:

`https://github.com/Analystshaik/Marketvector-15-Day-Forecast-TLT-Positive.git`

Branch:

`main`

Verify the configured remote with:

```bash
git remote -v
```

If configuration is ever needed from scratch:

```bash
git init
git branch -M main
git remote add origin https://github.com/Analystshaik/Marketvector-15-Day-Forecast-TLT-Positive.git
```

---

## 6. Streamlit Community Cloud

- Repository: `Analystshaik/Marketvector-15-Day-Forecast-TLT-Positive`
- Branch: `main`
- Main file path: `app.py`

Cloud database path:

`data\streamlit_market_data.sqlite`

---

## 7. Daily operation

The normal daily process should be:

```text
1. Refresh C:\MarketVector\Database\ibkr_market_data.sqlite
2. Double-click BUILD_AND_PUSH_DAILY.bat
3. Wait for SUCCESS
4. Verify Streamlit Cloud redeploys
```

A successful push should end with output similar to:

```text
main -> main

SUCCESS

GitHub has been updated successfully.
Streamlit Cloud should detect the new commit and redeploy.
```

`git lfs ls-files` should also list:

`data/streamlit_market_data.sqlite`

---

## 8. Safety notes

- Never push the full core database `C:\MarketVector\Database\ibkr_market_data.sqlite`.
- Push only the slim cloud DB under `data\streamlit_market_data.sqlite`.
- Keep SQLite files under Git LFS.
- Do not use force-push as part of the normal daily procedure.
- If `git pull --rebase` reports a conflict, resolve the conflict before continuing.
- If an unrelated file appears in final `git status`, such as a ZIP file, it was not pushed unless explicitly staged.
