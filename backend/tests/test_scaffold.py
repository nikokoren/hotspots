from hotspots import cli
from hotspots.config import load_config


def test_cli_help_runs():
    assert cli.main([]) == 0


def test_default_config_loads():
    cfg = load_config()
    assert cfg["firms"]["product"] == "VIIRS_SNPP_NRT"
    assert cfg["visual"]["expire_hours"] == 72
