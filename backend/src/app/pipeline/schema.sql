-- The platform's tables. Raw exports land in src_* as received; everything
-- else is derived by the pipeline or written by the governed workflow.

CREATE TABLE kv (k VARCHAR PRIMARY KEY, v VARCHAR);

-- ---- Raw exports (landed as received, read-only after the build) --------
CREATE TABLE src_staff (upn VARCHAR, display_name VARCHAR, role VARCHAR, office VARCHAR, status VARCHAR, left_on DATE);
CREATE TABLE src_survey (response_id VARCHAR, upn VARCHAR, tool_name VARCHAR, process VARCHAR, purpose VARCHAR,
                         repo VARCHAR, url VARCHAR, agent_id VARCHAR, users_estimate INTEGER, submitted_at TIMESTAMP);
CREATE TABLE src_identity (upn VARCHAR, platform VARCHAR, account VARCHAR);
CREATE TABLE src_github_repos (repo VARCHAR, owner_login VARCHAR, account_type VARCHAR, visibility VARCHAR,
                               language VARCHAR, created_at TIMESTAMP, pushed_at TIMESTAMP);
CREATE TABLE src_repo_files (repo VARCHAR, path VARCHAR, content VARCHAR, in_head BOOLEAN, commit_sha VARCHAR, committed_at TIMESTAMP);
CREATE TABLE src_netlify_sites (site_id VARCHAR, site_name VARCHAR, account VARCHAR, repo_url VARCHAR, custom_domain VARCHAR,
                                plan VARCHAR, visitors_30d INTEGER, requests_30d INTEGER, last_deploy_at TIMESTAMP);
CREATE TABLE src_firebase_projects (project_id VARCHAR, account VARCHAR, plan VARCHAR, hosting_url VARCHAR,
                                    collections VARCHAR, active_users_30d INTEGER, requests_30d INTEGER);
CREATE TABLE src_supabase_projects (ref VARCHAR, name VARCHAR, account VARCHAR, plan VARCHAR, db_size_mb INTEGER,
                                    tables VARCHAR, active_users_30d INTEGER, requests_30d INTEGER);
CREATE TABLE src_copilot_agents (agent_id VARCHAR, name VARCHAR, environment VARCHAR, owner_upn VARCHAR, connectors VARCHAR,
                                 knowledge VARCHAR, users_30d INTEGER, last_published TIMESTAMP);
CREATE TABLE src_dns (name VARCHAR, type VARCHAR, target VARCHAR);
CREATE TABLE src_billing (month VARCHAR, platform VARCHAR, account VARCHAR, resource VARCHAR, currency VARCHAR, amount_cents BIGINT);
CREATE TABLE src_expenses (claim_id VARCHAR, upn VARCHAR, month VARCHAR, vendor VARCHAR, description VARCHAR, amount_aud_cents BIGINT);
CREATE TABLE src_azure_resources (name VARCHAR, type VARCHAR, monthly_aud_cents BIGINT);
CREATE TABLE src_tf_state (name VARCHAR);
CREATE TABLE src_db_growth (resource VARCHAR, day DATE, size_mb INTEGER, limit_mb INTEGER);
CREATE TABLE src_cert (hostname VARCHAR, expires_on DATE, auto_renew BOOLEAN);
CREATE TABLE src_logs (tool_key VARCHAR, ts TIMESTAMP, level VARCHAR, line VARCHAR);
CREATE TABLE src_deploys (tool_key VARCHAR, ts TIMESTAMP, commit_sha VARCHAR, files VARCHAR, message VARCHAR);
CREATE TABLE src_config_changes (tool_key VARCHAR, ts TIMESTAMP, change VARCHAR, by_account VARCHAR);
CREATE TABLE src_provider_status (provider VARCHAR, started_at TIMESTAMP, ended_at TIMESTAMP, status VARCHAR, note VARCHAR);

-- ---- Derived: the register --------------------------------------------------
CREATE TABLE tool (tool_id VARCHAR PRIMARY KEY, key VARCHAR, name VARCHAR, declared BOOLEAN, process VARCHAR, purpose VARCHAR,
                   kind VARCHAR, owner_upn VARCHAR, owner_name VARCHAR, owner_role VARCHAR, office VARCHAR, owner_status VARCHAR,
                   owner_left_on DATE, repo VARCHAR, repo_candidates VARCHAR, repo_visibility VARCHAR, hosting VARCHAR,
                   site VARCHAR, database VARCHAR, db_ref VARCHAR, hostname VARCHAR, agent_id VARCHAR, ai_route VARCHAR,
                   users_30d INTEGER, requests_30d INTEGER, records BIGINT, data_classes VARCHAR, tier INTEGER, tier_reason VARCHAR,
                   monthly_cost_aud_cents BIGINT, paid_by VARCHAR, home VARCHAR, status VARCHAR, sources INTEGER);
CREATE TABLE tool_source (tool_id VARCHAR, source VARCHAR, ref VARCHAR, joined_by VARCHAR);
CREATE TABLE discovery_hold (hold_id VARCHAR, source VARCHAR, ref VARCHAR, reason VARCHAR, candidates VARCHAR, resolved_by VARCHAR);
CREATE TABLE register_flag (tool_id VARCHAR, flag VARCHAR, severity VARCHAR, detail VARCHAR);
CREATE TABLE ai_register (entry VARCHAR, route VARCHAR, approved BOOLEAN, data_allowed VARCHAR, users INTEGER, tools VARCHAR, evidence VARCHAR);

-- ---- The production gate ---------------------------------------------------
CREATE TABLE gate_finding (tool_id VARCHAR, rule_id VARCHAR, outcome VARCHAR, path VARCHAR, line INTEGER, evidence VARCHAR, detail VARCHAR);
CREATE TABLE gate_result (tool_id VARCHAR PRIMARY KEY, outcome VARCHAR, refuse_count INTEGER, hold_count INTEGER, scanned_files INTEGER, scanned_at TIMESTAMP);
CREATE TABLE gate_ablation (rule_id VARCHAR, tools_through INTEGER, personal_records_exposed BIGINT, live_secrets INTEGER, users_exposed INTEGER, tools VARCHAR);
CREATE TABLE secret_rotation (fingerprint VARCHAR, tool_id VARCHAR, rotated_at TIMESTAMP, rotated_by VARCHAR);
CREATE TABLE repo_fix (repo VARCHAR, path VARCHAR, content VARCHAR, note VARCHAR);

-- ---- Monitoring -------------------------------------------------------------
CREATE TABLE alert_raw (alert_id VARCHAR, ts TIMESTAMP, tool_key VARCHAR, monitor VARCHAR, signal VARCHAR, region VARCHAR,
                        severity VARCHAR, fingerprint VARCHAR, value INTEGER, threshold INTEGER, after_idle BOOLEAN, incident_id VARCHAR);
CREATE TABLE alert_decision (alert_id VARCHAR, rule VARCHAR, page_id VARCHAR);
CREATE TABLE page (page_id VARCHAR, tool_key VARCHAR, opened_at TIMESTAMP, closed_at TIMESTAMP, alerts INTEGER, signals VARCHAR, incident_id VARCHAR);
CREATE TABLE noise_ablation (rule VARCHAR, setting VARCHAR, pages INTEGER, incidents_paged INTEGER, incidents_missed VARCHAR, minutes_to_page_max INTEGER);
CREATE TABLE incident_world (incident_id VARCHAR, page_id VARCHAR, tool_key VARCHAR, opened_at TIMESTAMP, first_signal VARCHAR, summary VARCHAR, world VARCHAR);
CREATE TABLE forecast (resource VARCHAR, kind VARCHAR, now_value INTEGER, limit_value INTEGER, per_day_x100 INTEGER, days_left INTEGER, due_on DATE);

-- ---- Cost -------------------------------------------------------------------
CREATE TABLE cost_line (month VARCHAR, platform VARCHAR, account VARCHAR, resource VARCHAR, tool_id VARCHAR, aud_cents BIGINT, basis VARCHAR);
CREATE TABLE cost_finding (finding_id VARCHAR, kind VARCHAR, tool_id VARCHAR, resource VARCHAR, monthly_aud_cents BIGINT, detail VARCHAR, action VARCHAR);

-- ---- Governed workflow -------------------------------------------------------
CREATE TABLE change_request (cr_id VARCHAR PRIMARY KEY, tool_id VARCHAR, kind VARCHAR, target VARCHAR, title VARCHAR, reason VARCHAR,
                             proposed_by VARCHAR, proposed_at TIMESTAMP, status VARCHAR, decided_by VARCHAR, decided_at TIMESTAMP,
                             decision_note VARCHAR, implemented_by VARCHAR, implemented_at TIMESTAMP, evidence VARCHAR);
CREATE TABLE audit_log (audit_id INTEGER, ts TIMESTAMP, actor VARCHAR, system VARCHAR, project_id VARCHAR, subject VARCHAR,
                        action VARCHAR, outcome VARCHAR, detail VARCHAR, reason VARCHAR);
