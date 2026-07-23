from __future__ import annotations

import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEPLOY = ROOT / "deploy"


def test_deploy_shell_scripts_have_valid_syntax() -> None:
    scripts = sorted(DEPLOY.glob("*.sh"))
    result = subprocess.run(
        ["bash", "-n", *map(str, scripts)],
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr


def test_application_services_restart_without_start_limit() -> None:
    for filename in ("gusto-public.service", "gusto-admin.service"):
        content = (DEPLOY / filename).read_text(encoding="utf-8")
        assert "Restart=always" in content
        assert "StartLimitIntervalSec=0" in content
        assert "WantedBy=multi-user.target" in content


def test_reconcile_timer_runs_after_boot_and_periodically() -> None:
    content = (DEPLOY / "gusto-reconcile.timer").read_text(encoding="utf-8")
    assert "OnBootSec=45s" in content
    assert "OnUnitActiveSec=5min" in content
    assert "Persistent=true" in content
    assert "WantedBy=timers.target" in content


def test_funnel_reconciliation_only_manages_port_8443() -> None:
    content = (DEPLOY / "configure-funnel.sh").read_text(encoding="utf-8")
    assert "--https=8443" in content
    assert "--https=443" not in content
    assert "--https=8444" not in content
