# gusto_cantgohome

ガストの人気メニュートップ10を複数人で当てるための共有Webアプリケーションです。

## 開発

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[dev]'
ruff check .
python -m pytest
uvicorn app.public_app:app --reload
```

## GitHub運用

- Issue-firstで作業する。
- 1 Issueは1成果または判断単位、1 commitは1論理単位、1 PRは1成果とする。
- Pull Requestは通常のmerge commitで統合し、squash mergeは使用しない。
- mergeは明示的な承認後にのみ行う。
- ランキングデータ、SQLite、credentialはGitへ含めない。
