"""Generate the agency's data from a seed.

Deterministic: one seed, integer draws only, so the output is byte-identical
on any machine and the build can check it against pinned digests.

Sales: every sales agent appraises most weeks; some appraisals become
listings, by private treaty or auction; listings go under contract, are
withdrawn or are still on the market; contracts settle. Rentals: every
property manager looks after a rent roll; tenancies run on twelve-month
leases, renew or end, and the property sits vacant before the next one;
arrears are recorded weekly; maintenance jobs and bonds follow each tenancy.

Then the data-entry errors in reference.SEEDED are put in, and recorded in
truth_defect - which the checks never read.
"""

from __future__ import annotations

import random
from datetime import date, timedelta

import duckdb
import pandas as pd

from src.app.pipeline import reference as ref

DAY = timedelta(days=1)


def _ins(con: duckdb.DuckDBPyConnection, table: str, rows: list) -> None:
    """Bulk insert through a frame: row-by-row inserts take most of a minute."""
    if not rows:
        return
    cols = [c[0] for c in con.execute(f"SELECT * FROM {table} LIMIT 0").description]
    frame = pd.DataFrame([tuple(r) for r in rows], columns=cols).astype(object)
    con.register("_rows", frame)
    con.execute(f"INSERT INTO {table} SELECT * FROM _rows")
    con.unregister("_rows")


def _round(v: int, step: int) -> int:
    return (v + step // 2) // step * step


def generate(con: duckdb.DuckDBPyConnection) -> dict:
    rng = random.Random(ref.SEED)
    r = rng.randrange
    days_total = (ref.TODAY - ref.HISTORY_START).days

    offices, staff = [], []
    sales_agents: dict[str, list[str]] = {}
    pms: dict[str, list[str]] = {}
    used_names = set()

    def name() -> str:
        while True:
            n = f"{ref.FIRST[r(len(ref.FIRST))]} {ref.LAST[r(len(ref.LAST))]}."
            if n not in used_names:
                used_names.add(n)
                return n

    for code, label, region in ref.OFFICES:
        median = _round(650_000 + r(950_000), 5_000) * 100
        offices.append((code, label, region, median))
        sales_agents[code] = []
        for i in range(4 + r(7)):
            sid = f"{code}-S{i + 1:02d}"
            staff.append((sid, name(), code, "sales"))
            sales_agents[code].append(sid)
        pms[code] = []
        for i in range(2 + r(5)):
            sid = f"{code}-P{i + 1:02d}"
            staff.append((sid, name(), code, "property"))
            pms[code].append(sid)
    _ins(con, "office", offices)
    _ins(con, "staff", staff)
    median_of = {o[0]: o[3] for o in offices}

    # ---- Sales -------------------------------------------------------------------
    appraisals, listings, splits, marketing, enquiries = [], [], [], [], []
    n_app = n_list = 0
    for code, label, _region in ref.OFFICES:
        for agent in sales_agents[code]:
            for week in range(days_total // 7):
                for _ in range([0, 1, 1, 2, 2, 2, 3, 4][r(8)]):
                    n_app += 1
                    on = ref.HISTORY_START + timedelta(days=week * 7 + r(7))
                    value = _round(median_of[code] * (60 + r(110)) // 100, 500_000)
                    addr = f"{1 + r(240)} {ref.STREETS[r(len(ref.STREETS))]}, Suburb {code}{1 + r(4)}"
                    aid = f"AP-{n_app:06d}"
                    appraisals.append((aid, code, agent, addr, on, value * 95 // 100, value * 105 // 100))
                    if r(100) >= 38:
                        continue
                    listed_on = on + timedelta(days=7 + r(39))
                    if listed_on > ref.TODAY:
                        continue
                    n_list += 1
                    lid = f"L-{n_list:06d}"
                    method = "auction" if r(100) < 30 else "private treaty"
                    status, result, withdrawn, contract, settle, price = "active", None, None, None, None, None
                    roll = r(100)
                    if method == "auction":
                        auction_day = listed_on + timedelta(days=28 + r(8))
                        if auction_day <= ref.TODAY:
                            if r(100) < 64:
                                result, contract = "sold", auction_day
                            else:
                                result = "passed in"
                                if r(100) < 60:
                                    contract = auction_day + timedelta(days=5 + r(55))
                                elif r(100) < 40:
                                    withdrawn = auction_day + timedelta(days=10 + r(40))
                    elif roll < 74:
                        contract = listed_on + timedelta(days=9 + r(85))
                    elif roll < 88:
                        withdrawn = listed_on + timedelta(days=30 + r(90))
                    if contract and contract > ref.TODAY:
                        contract = None
                    if not contract and not withdrawn:
                        # Unsold after about four months, a campaign comes off the market.
                        withdrawn = listed_on + timedelta(days=110 + r(40))
                    if withdrawn and withdrawn > ref.TODAY:
                        withdrawn = None
                    if contract:
                        price = _round(value * (92 + r(17)) // 100, 100_000)
                        settle = contract + timedelta(days=30 + r(31))
                        status = "settled" if settle <= ref.TODAY else "under contract"
                    elif withdrawn:
                        status = "withdrawn"
                    rate = ref.COMMISSION_BP[0] + r((ref.COMMISSION_BP[1] - ref.COMMISSION_BP[0]) // 5 + 1) * 5
                    listings.append([lid, aid, code, agent, addr, listed_on, method, status, result, withdrawn, contract, settle, price, rate])
                    if contract:
                        seller = sales_agents[code][r(len(sales_agents[code]))]
                        if seller == agent:
                            splits.append([lid, agent, 10_000])
                        else:
                            splits += [[lid, agent, 5_000], [lid, seller, 5_000]]
                    budget = (1_500 + r(46) * 100) * 100
                    marketing.append((lid, budget, budget * (82 + r(36)) // 100))
                    weight = 1 if status == "withdrawn" else 2
                    for ch, base in zip(ref.CHANNELS, (24, 14, 9, 4, 6)):
                        enquiries.append((lid, ch, (base + r(base + 1)) * weight // 2))

    # ---- Rentals ------------------------------------------------------------------
    properties, tenancies, snaps, jobs, bonds = [], [], [], [], []
    n_prop = n_ten = n_job = 0
    weeks = [ref.HISTORY_START + timedelta(days=6 + 7 * i) for i in range(days_total // 7)]
    for code, _label, _region in ref.OFFICES:
        for pm in pms[code]:
            for _ in range(95 + r(46)):
                n_prop += 1
                pid = f"PR-{n_prop:06d}"
                properties.append((pid, code, pm, f"{1 + r(240)}/{1 + r(30)} {ref.STREETS[r(len(ref.STREETS))]}, Suburb {code}{1 + r(4)}"))
                rent = (420 + r(56) * 10) * 100
                start = ref.HISTORY_START - timedelta(days=r(365))
                renewal = False
                while start <= ref.TODAY:
                    n_ten += 1
                    tid = f"T-{n_ten:06d}"
                    lease_end = start + timedelta(days=364)
                    renews = r(100) < 68
                    end = None if renews else lease_end - timedelta(days=r(20))
                    if end and end > ref.TODAY:
                        end = None
                    tenancies.append([tid, pid, code, pm, rent, start, lease_end, end, renewal])
                    if start >= ref.HISTORY_START:
                        received = start - timedelta(days=r(6))
                        lodged = received + timedelta(days=(11 + r(20)) if r(100) < 4 else 1 + r(9))
                        bonds.append((f"B-{n_ten:06d}", tid, code, rent * 4, received, lodged if lodged <= ref.TODAY else None))
                    habit = r(1000)
                    run = 0
                    last = min(end or lease_end, ref.TODAY)
                    for wk in weeks:
                        if wk < start or wk > last:
                            continue
                        days = 0
                        if habit < 25:      # chronic: arrears build
                            run = min(run + r(5), 70) if r(100) < 85 else 0
                            days = run
                        elif habit < 100:   # sometimes late
                            days = 1 + r(14) if r(100) < 30 else 0
                        elif r(100) < 3:
                            days = 1 + r(6)
                        if days:
                            snaps.append((wk, tid, days, rent * days // 7))
                        if r(1000) < 38:
                            n_job += 1
                            reported = wk - timedelta(days=r(7))
                            urgent = r(100) < 11
                            done = reported + timedelta(days=(r(4) if r(100) < 85 else 4 + r(10)) if urgent else 2 + r(30))
                            jobs.append((f"J-{n_job:06d}", tid, code, ref.MAINTENANCE[r(len(ref.MAINTENANCE))], "urgent" if urgent else "routine",
                                         reported, done if done <= ref.TODAY else None, (80 + r(1420)) * 100))
                    if end is None and lease_end <= ref.TODAY:
                        # Renewed: this lease ends, and the same tenants start a new one, rent up a little.
                        tenancies[-1][7] = lease_end
                        start, renewal, rent = lease_end + DAY, True, _round(rent * (102 + r(5)) // 100, 500)
                    elif end is None:
                        break
                    else:
                        start, renewal, rent = end + timedelta(days=5 + r(36)), False, _round(rent * (100 + r(7)) // 100, 500)

    # ---- Seeded data-entry errors -----------------------------------------------------
    truth = []
    sold = [l for l in listings if l[10]]
    pick = lambda pool, n: [pool[i] for i in sorted(rng.sample(range(len(pool)), n))]  # noqa: E731
    seen_ids: set[str] = set()

    def fresh(pool, n):
        out = []
        for item in pick([p for p in pool if p[0] not in seen_ids], n):
            seen_ids.add(item[0])
            out.append(item)
        return out

    for l in fresh([l for l in listings if l[7] in ("settled", "under contract")], ref.SEEDED["settlement_before_contract"]):
        l[11] = l[10] - timedelta(days=3 + r(10))
        truth.append(("settlement_before_contract", l[0]))
    for l in fresh(sold, ref.SEEDED["price_extra_digit"]):
        l[12] = l[12] * 10
        truth.append(("price_extra_digit", l[0]))
    for l in fresh([l for l in listings if l[7] == "active"], ref.SEEDED["listing_without_agent"]):
        l[3] = None
        truth.append(("listing_without_agent", l[0]))
    split_lids = {s[0] for s in splits if s[2] == 5_000}
    for l in fresh([l for l in sold if l[0] in split_lids], ref.SEEDED["commission_split_not_100"]):
        for s in splits:
            if s[0] == l[0]:
                s[2] = 4_000
                break
        truth.append(("commission_split_not_100", l[0]))
    for l in fresh([l for l in listings if l[5] < ref.TODAY - timedelta(days=40)], ref.SEEDED["duplicate_listing"]):
        n_list += 1
        other = ref.OFFICES[(ord(l[2]) - 65 + 1) % 26][0]
        dup = [f"L-{n_list:06d}", None, other, sales_agents[other][0], l[4], l[5] + timedelta(days=2 + r(20)), l[6], "active",
               None, None, None, None, None, l[13]]
        listings.append(dup)
        marketing.append((dup[0], 1_500_00, 0))
        truth.append(("duplicate_listing", dup[0]))
    ended = [t for t in tenancies if t[7] and t[7] < ref.TODAY - timedelta(days=21)]
    for t in pick(ended, ref.SEEDED["arrears_after_vacate"]):
        wk = next(w for w in weeks if w > t[7] + timedelta(days=7))
        snaps.append((wk, t[0], 9 + r(20), t[4] * 2))
        truth.append(("arrears_after_vacate", t[0]))
    for i in range(ref.SEEDED["bond_without_tenancy"]):
        code = ref.OFFICES[r(26)][0]
        received = ref.TODAY - timedelta(days=20 + r(200))
        bid = f"B-X{i + 1:04d}"
        bonds.append((bid, f"T-{900_000 + r(99_999):06d}", code, (450 + r(40) * 10) * 400, received, received + timedelta(days=2 + r(6))))
        truth.append(("bond_without_tenancy", bid))

    _ins(con, "appraisal", appraisals)
    _ins(con, "listing", [tuple(l) for l in listings])
    _ins(con, "commission_split", [tuple(s) for s in splits])
    _ins(con, "marketing", marketing)
    _ins(con, "enquiry", enquiries)
    _ins(con, "property", properties)
    _ins(con, "tenancy", [tuple(t) for t in tenancies])
    _ins(con, "arrears_snapshot", snaps)
    _ins(con, "maintenance", jobs)
    _ins(con, "bond", bonds)
    _ins(con, "truth_defect", truth)
    return {"appraisals": len(appraisals), "listings": len(listings), "tenancies": len(tenancies), "arrears_rows": len(snaps)}
