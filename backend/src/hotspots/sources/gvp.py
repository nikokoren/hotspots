"""Smithsonian Global Volcanism Program — volcano catalogue (WFS) and weekly reports.

WFS:     https://webservices.volcano.si.edu/geoserver/GVP-VOTW/wfs?request=GetCapabilities
Docs:    https://volcano.si.edu/database/webservices.cfm
Weekly:  https://volcano.si.edu/reports_weekly.cfm?vtab=feeds

Layer and field selection still to be decided after inspecting GetCapabilities.
"""

from __future__ import annotations

WFS_URL = "https://webservices.volcano.si.edu/geoserver/GVP-VOTW/wfs"


def fetch_catalogue(timeout_s: float):
    raise NotImplementedError


def fetch_weekly_reports(timeout_s: float):
    raise NotImplementedError
