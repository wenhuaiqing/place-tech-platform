"""The noise rules: fewer pages, no incident hidden, alternatives scored."""

from __future__ import annotations

import re
from datetime import datetime, timedelta

from src.app.pipeline import monitoring as mon
from src.app.pipeline import reference as ref


def test_every_incident_pages_and_pages_fall(built):
    rows = {r[0]: r for r in built.execute("SELECT * FROM noise_ablation").fetchall()}
    assert rows["All rules"][3] == len(ref.INCIDENTS)
    assert rows["All rules"][2] * 20 < rows["Every alert pages"][2]


def test_each_rule_earns_its_place(built):
    rows = dict(built.execute("SELECT rule, pages FROM noise_ablation").fetchall())
    for name in ("Without the maintenance window", "Without de-duplication", "Without the first-request rule",
                 "Without probe confirmation", "Without the persistence rule", "Without grouping"):
        assert rows[name] > rows["All rules"], name


def test_rejected_alternatives_cost_something(built):
    rows = {r[0]: r for r in built.execute("SELECT * FROM noise_ablation").fetchall()}
    assert rows["Require all three probe regions"][4] == "INC-03"
    assert rows["Drop all latency alerts"][5] > rows["All rules"][5]


def test_duplicate_pairs_with_one_original_only():
    t0 = datetime(2026, 10, 1, 9)
    alerts = [("a1", t0, "x", "m1", "latency_p95", None, False), ("a2", t0 + timedelta(minutes=2), "x", "m2", "latency_p95", None, False),
              ("a3", t0 + timedelta(minutes=4), "x", "m1", "latency_p95", None, False)]
    decisions, _ = mon.process(alerts, {**mon.DEFAULT, "persist": False})
    by = {d[0]: d[1] for d in decisions}
    assert by["a2"] == "duplicate from a second monitor"
    assert by["a3"] != "duplicate from a second monitor"


def test_snapshots_carry_no_personal_details(built):
    raw = " ".join(r[0] for r in built.execute("SELECT line FROM src_logs").fetchall())
    assert re.search(r"@mail\.example", raw)  # the raw logs do have them
    for (w,) in built.execute("SELECT world FROM incident_world").fetchall():
        assert not re.search(r"[\w.]+@[\w-]+\.\w+|04\d{2} \d{3} \d{3}", w)


def test_mask():
    assert mon.mask("by a.b@mail.example on 0400 123 456 for 14 Example St") == "by [email] on [phone] for [address]"
