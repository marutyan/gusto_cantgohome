# gusto_cantgohome

ガストの人気メニュートップ10を複数人で当てる共有Webアプリケーションです。未回答メニューの順位はブラウザへ送らず、回答送信後にだけ公開します。

## 開発

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[dev]'
python scripts/migrate.py --db data/gusto.sqlite3
ruff check .
pytest --ignore=tests/e2e
python -m playwright install chromium
pytest tests/e2e
uvicorn app.public_app:app --reload --port 8010
```

ランキングXLSX・CSV、SQLite、バックアップ、credential、`.env`はGitへ含めません。`scripts/import_rankings.py`でprivateファイルからDBへ直接取り込みます。

## GitHub運用

- Issue-firstで作業する。
- 1 Issueは1成果または判断単位、1 commitは1論理単位、1 PRは1成果とする。
- Pull Requestは通常のmerge commitで統合し、squash mergeは使用しない。
- mergeは明示的な承認後にのみ行う。
