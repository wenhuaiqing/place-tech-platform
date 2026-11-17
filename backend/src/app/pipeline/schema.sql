-- The agency's data, as its sales and property management systems would hold
-- it. Money is in cents. Raw tables are written by the generator; the data
-- checks write check_result and quarantine; the reports read the v_* views.

CREATE TABLE kv (k VARCHAR PRIMARY KEY, v VARCHAR);

CREATE TABLE office (office_code VARCHAR PRIMARY KEY, office VARCHAR, region VARCHAR, median_price_cents BIGINT);
CREATE TABLE staff (staff_id VARCHAR PRIMARY KEY, name VARCHAR, office_code VARCHAR, role VARCHAR);

CREATE TABLE appraisal (appraisal_id VARCHAR PRIMARY KEY, office_code VARCHAR, agent_id VARCHAR, address VARCHAR,
                        appraised_on DATE, estimate_low_cents BIGINT, estimate_high_cents BIGINT);
CREATE TABLE listing (listing_id VARCHAR PRIMARY KEY, appraisal_id VARCHAR, office_code VARCHAR, agent_id VARCHAR, address VARCHAR,
                      listed_on DATE, method VARCHAR, status VARCHAR, auction_result VARCHAR, withdrawn_on DATE,
                      contract_on DATE, settle_on DATE, price_cents BIGINT, commission_bp INTEGER);
CREATE TABLE commission_split (listing_id VARCHAR, agent_id VARCHAR, share_bp INTEGER);
CREATE TABLE marketing (listing_id VARCHAR PRIMARY KEY, budget_cents BIGINT, spend_cents BIGINT);
CREATE TABLE enquiry (listing_id VARCHAR, channel VARCHAR, enquiries INTEGER);

CREATE TABLE property (property_id VARCHAR PRIMARY KEY, office_code VARCHAR, pm_id VARCHAR, address VARCHAR);
CREATE TABLE tenancy (tenancy_id VARCHAR PRIMARY KEY, property_id VARCHAR, office_code VARCHAR, pm_id VARCHAR, weekly_rent_cents BIGINT,
                      start_on DATE, lease_end DATE, end_on DATE, renewal BOOLEAN);
CREATE TABLE arrears_snapshot (week_ending DATE, tenancy_id VARCHAR, days INTEGER, amount_cents BIGINT);
CREATE TABLE maintenance (job_id VARCHAR PRIMARY KEY, tenancy_id VARCHAR, office_code VARCHAR, category VARCHAR, priority VARCHAR,
                          reported_on DATE, completed_on DATE, cost_cents BIGINT);
CREATE TABLE bond (bond_id VARCHAR PRIMARY KEY, tenancy_id VARCHAR, office_code VARCHAR, amount_cents BIGINT, received_on DATE, lodged_on DATE);

-- What the generator seeded. The checks never read this; the tests compare against it.
CREATE TABLE truth_defect (defect VARCHAR, record_id VARCHAR);

CREATE TABLE check_result (check_id VARCHAR, record_kind VARCHAR, record_id VARCHAR, office_code VARCHAR, detail VARCHAR);
CREATE TABLE quarantine (record_kind VARCHAR, record_id VARCHAR, check_id VARCHAR);

-- Written at run time: one row per assistant run (never the visitor's words), and the audit log.
CREATE TABLE agent_run (ts TIMESTAMP, page VARCHAR, agents VARCHAR, engine VARCHAR, ok BOOLEAN, errors INTEGER, duration_ms INTEGER);
CREATE TABLE audit_log (audit_id INTEGER, ts TIMESTAMP, actor VARCHAR, system VARCHAR, project_id VARCHAR, subject VARCHAR,
                        action VARCHAR, outcome VARCHAR, detail VARCHAR, reason VARCHAR);
