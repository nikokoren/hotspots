from hotspots import cli


def test_cli_help_runs():
    assert cli.main([]) == 0
