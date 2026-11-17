-- What the reports, the assistant and the Ask page read. Quarantined records
-- are left out here, once, so no report can forget to.

CREATE VIEW v_offices AS SELECT office_code, office, region FROM office;

CREATE VIEW v_staff AS SELECT staff_id, name, office_code, role FROM staff;

CREATE VIEW v_appraisals AS
SELECT a.appraisal_id, a.office_code, a.agent_id, a.appraised_on, a.estimate_low_cents / 100 AS estimate_low, a.estimate_high_cents / 100 AS estimate_high,
       l.listing_id IS NOT NULL AS became_listing
FROM appraisal a LEFT JOIN listing l USING (appraisal_id);

CREATE VIEW v_listings AS
SELECT l.listing_id, l.office_code, l.agent_id, l.address, l.listed_on, l.method, l.status, l.auction_result, l.withdrawn_on,
       l.contract_on, l.settle_on, l.price_cents / 100 AS price, l.commission_bp,
       l.price_cents * l.commission_bp // 1000000 AS commission,
       CASE WHEN l.contract_on IS NOT NULL THEN datediff('day', l.listed_on, l.contract_on) END AS days_on_market,
       a.estimate_low_cents / 100 AS appraisal_low, a.estimate_high_cents / 100 AS appraisal_high
FROM listing l LEFT JOIN appraisal a USING (appraisal_id)
WHERE l.listing_id NOT IN (SELECT record_id FROM quarantine WHERE record_kind = 'listing');

-- Sales: one row per contract. Settled when settle_on is on or before today.
CREATE VIEW v_sales AS SELECT * FROM v_listings WHERE contract_on IS NOT NULL;

CREATE VIEW v_commission_by_agent AS
SELECT s.listing_id, s.agent_id, l.office_code, l.contract_on, l.settle_on, l.commission * s.share_bp // 10000 AS commission_share
FROM commission_split s JOIN v_sales l USING (listing_id)
WHERE s.listing_id NOT IN (SELECT record_id FROM check_result WHERE check_id IN ('C03', 'C06'));

CREATE VIEW v_tenancies AS
SELECT t.tenancy_id, t.property_id, t.office_code, t.pm_id, t.weekly_rent_cents / 100 AS weekly_rent, t.start_on, t.lease_end, t.end_on,
       t.renewal, t.end_on IS NULL AS current
FROM tenancy t;

CREATE VIEW v_arrears AS
SELECT s.week_ending, s.tenancy_id, t.office_code, t.pm_id, s.days, s.amount_cents / 100 AS amount
FROM arrears_snapshot s JOIN tenancy t USING (tenancy_id)
WHERE t.end_on IS NULL OR s.week_ending <= t.end_on;

CREATE VIEW v_maintenance AS
SELECT job_id, tenancy_id, office_code, category, priority, reported_on, completed_on, cost_cents / 100 AS cost,
       datediff('day', reported_on, coalesce(completed_on, (SELECT CAST(v AS DATE) FROM kv WHERE k = 'today'))) AS days_open
FROM maintenance;

CREATE VIEW v_bonds AS
SELECT bond_id, tenancy_id, office_code, amount_cents / 100 AS amount, received_on, lodged_on,
       datediff('day', received_on, lodged_on) AS days_to_lodge
FROM bond WHERE bond_id NOT IN (SELECT record_id FROM quarantine WHERE record_kind = 'bond');

CREATE VIEW v_marketing AS
SELECT m.listing_id, l.office_code, l.status, m.budget_cents / 100 AS budget, m.spend_cents / 100 AS spend,
       (SELECT sum(enquiries) FROM enquiry e WHERE e.listing_id = m.listing_id) AS enquiries
FROM marketing m JOIN v_listings l USING (listing_id);

CREATE VIEW v_enquiries AS
SELECT e.listing_id, l.office_code, e.channel, e.enquiries FROM enquiry e JOIN v_listings l USING (listing_id);

-- A re-let: a new (not renewed) tenancy after the property sat empty.
CREATE VIEW v_vacancies AS
SELECT t.property_id, t.office_code, t.tenancy_id, prev.end_on AS vacated_on, t.start_on AS relet_on,
       datediff('day', prev.end_on, t.start_on) AS vacant_days
FROM tenancy t JOIN tenancy prev ON prev.property_id = t.property_id AND prev.end_on < t.start_on
     AND NOT EXISTS (SELECT 1 FROM tenancy mid WHERE mid.property_id = t.property_id AND mid.start_on > prev.start_on AND mid.start_on < t.start_on)
WHERE NOT t.renewal;
