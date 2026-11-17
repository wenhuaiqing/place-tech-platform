"""Everything the synthetic world is made of, declared once.

The tools, the people who built them, the exports the inventory is built
from, and every defect seeded into them. The pipeline never reads the
`SEEDED` lists: it finds each defect from the data, and the tests check that
what it found is what was seeded. Nothing here describes Place's real
tools, systems or people - they are invented, of the kinds the advertisement
says exist (Claude and Copilot Studio tools on Supabase, Firebase, Netlify
and personal GitHub).
"""

from __future__ import annotations

from datetime import date, datetime

SEED = 20261116
DEMO_TODAY = date(2026, 11, 16)
DEMO_NOW = datetime(2026, 11, 16, 9, 0, 0)
EXPORTS_TAKEN = datetime(2026, 11, 16, 6, 0, 0)

# Synthetic domain for every hostname, so nothing resolves to a real system.
DOMAIN = "place-tools.example"
STAFF_DOMAIN = "staff.example"

# From the advertisement: the MSP looks after 26 offices and about 700 staff.
OFFICES = [f"Office {chr(65 + i)}" for i in range(26)]
STAFF_TOTAL = 700

# ---- Money -----------------------------------------------------------------
# The hosting platforms bill in US dollars. ASSUMPTION: one rate for the
# whole period, in basis points of A$ per US$. Labelled on every page that
# converts; the finance team's rate replaces it.
AUD_PER_USD_BP = 15_500

# ---- People ---------------------------------------------------------------
# Invented. upn -> (display name, role, office, left_on or None)
STAFF = {
    "mia.k": ("Mia K.", "Property manager", "Office K", None),
    "noah.b": ("Noah B.", "Sales associate", "Office B", None),
    "ella.r": ("Ella R.", "Marketing coordinator", "HQ", None),
    "liam.d": ("Liam D.", "Principal", "Office D", None),
    "zoe.m": ("Zoe M.", "Leasing consultant", "Office M", None),
    "jack.t": ("Jack T.", "Sales agent", "Office T", None),
    "ruby.s": ("Ruby S.", "Trust accountant", "HQ", None),
    "oscar.p": ("Oscar P.", "Business manager", "Office P", None),
    "chloe.w": ("Chloe W.", "Property manager", "Office W", date(2026, 8, 29)),
    "leo.h": ("Leo H.", "Sales associate", "Office H", None),
    "isla.c": ("Isla C.", "Operations coordinator", "HQ", None),
    "max.f": ("Max F.", "Sales agent", "Office F", date(2026, 9, 25)),
    "ivy.g": ("Ivy G.", "Head of property management", "Office G", None),
    "hugo.n": ("Hugo N.", "Marketing coordinator", "HQ", None),
    "aria.l": ("Aria L.", "Leasing consultant", "Office L", date(2026, 10, 10)),
    "theo.v": ("Theo V.", "Sales associate", "Office V", None),
    "lucy.e": ("Lucy E.", "People and culture", "HQ", None),
    "finn.a": ("Finn A.", "Sales agent", "Office A", None),
    "sophie.q": ("Sophie Q.", "Property manager", "Office Q", None),
    "ben.y": ("Ben Y.", "Data and reporting", "HQ", None),
}

# Who acts in the demo. Roles, not people: the advertisement names real
# people, and nothing here speaks for them.
PEOPLE = {
    "builders": ["Builder - Mia K.", "Builder - Ella R.", "Builder - Ruby S."],
    "platform": ["Platform lead"],
    "cab": ["CAB - Head of Innovation", "CAB - Business Systems", "CAB - MSP change manager"],
}
CAB_MEMBERS = set(PEOPLE["cab"])
IMPLEMENTERS = {"Platform lead"}

# ---- The tools --------------------------------------------------------------
# kind: web (a site, maybe with a database), script (runs on someone's
# laptop), agent (Copilot Studio). Each web tool's front end, database and
# repository are separate rows in separate exports; the pipeline joins them
# by the keys they share, never by name.
#
# tables: (name, columns, rows) - the database the tool keeps. The data
# classes are worked out from the column names, by the pipeline.
TOOLS = [
    dict(key="appraisal-writer", name="Appraisal letter writer", owner="noah.b", kind="web",
         purpose="Drafts appraisal letters to vendors with Claude from the agent's notes.",
         repo="noah-b/appraisal-writer", hosting="netlify", site="appraisal-writer", database="supabase", ref="qpwlkxzvhatbrfgj",
         ai="anthropic_api", users=34, dns="appraisals",
         tables=[("appraisals", ["vendor_name", "vendor_email", "property_address", "estimate_low", "estimate_high", "notes"], 2140)]),
    dict(key="appraisal-gen", name="Appraisal generator", owner="theo.v", kind="web",
         purpose="Generates appraisal letters from a form; built separately at another office.",
         repo="theov/appraisal-gen", hosting="firebase", project="appraisal-gen-7f2c", database="firestore",
         ai="anthropic_api", users=9,
         tables=[("letters", ["vendor_name", "vendor_phone", "property_address", "estimate", "created_by"], 410)]),
    dict(key="listing-copy", name="Listing copy assistant", owner="ella.r", kind="web",
         purpose="Suggests listing headlines and copy from property features.",
         repo="ellar-place/listing-copy", hosting="netlify", site="listing-copy", database=None,
         ai="anthropic_api", users=88, tables=[]),
    dict(key="open-home", name="Open home sign-in", owner="jack.t", kind="web",
         purpose="Buyers sign in at open homes on a tablet; agents follow up from the list.",
         repo="jackt/open-home-signin", hosting="firebase", project="open-home-signin", database="firestore",
         ai=None, users=61, dns="openhome",
         tables=[("visitors", ["buyer_name", "buyer_email", "buyer_phone", "property_address", "visited_at"], 18_420)]),
    dict(key="arrears", name="Rental arrears tracker", owner="mia.k", kind="web",
         purpose="Lists tenants in arrears each morning with the days overdue.",
         repo="miak/arrears-tracker", hosting="netlify", site="arrears", database="supabase", ref="hyzmwkqoplrtcsda",
         ai=None, users=22,
         tables=[("arrears", ["tenant_name", "tenant_phone", "property_address", "rent_cents", "days_overdue"], 960)]),
    dict(key="vendor-report", name="Vendor weekly report", owner="leo.h", kind="web",
         purpose="Builds the weekly campaign report for vendors: enquiries, inspections, feedback.",
         repo="leoh/vendor-report", hosting="netlify", site="vendor-report", database="supabase", ref="bnvzqwtyulkhxmop",
         ai=None, users=47, dns="vendor-reports",
         tables=[("reports", ["vendor_name", "vendor_email", "property_address", "enquiries", "inspections", "feedback"], 3_310)]),
    dict(key="commission-calc", name="Commission split calculator", owner="oscar.p", kind="web",
         purpose="Works out commission splits between listing and selling agents.",
         repo="oscarp/commission-calc", hosting="netlify", site="commission-calc", database=None,
         ai=None, users=73, tables=[]),
    dict(key="key-register", name="Key register", owner="ivy.g", kind="web",
         purpose="Which key set is out, with whom, since when.",
         repo="ivyg/key-register", hosting="netlify", site="key-register", database="supabase", ref="cxqprzmwlfkeojtd",
         ai=None, users=4,
         tables=[("keys", ["key_tag", "property_address", "issued_to", "issued_at", "returned_at"], 5_820)]),
    dict(key="maintenance-agent", name="Maintenance request triage", owner="zoe.m", kind="agent",
         purpose="A Copilot Studio agent that reads tenant maintenance emails and drafts the work order.",
         agent_id="cs-maint-0193", connectors=["Office 365 Outlook", "Gmail (personal)"], ai="copilot_studio", users=18,
         tables=[]),
    dict(key="buyer-followup", name="Buyer follow-up reminders", owner="finn.a", kind="web",
         purpose="Reminds agents to call buyers back after an inspection.",
         repo="finna/buyer-followup", hosting="netlify", site="buyer-followup", database="supabase", ref="dkrmzqvwxlpaoyth",
         ai=None, users=29,
         tables=[("followups", ["buyer_name", "buyer_phone", "buyer_email", "property_address", "due_at"], 7_150)]),
    dict(key="social-scheduler", name="Social post scheduler", owner="hugo.n", kind="web",
         purpose="Queues listing posts for the office social accounts.",
         repo="hugon/social-scheduler", hosting="netlify", site="social-scheduler", database=None,
         ai="anthropic_api", users=12, tables=[]),
    dict(key="suburb-report", name="Suburb report generator", owner="ella.r", kind="web",
         purpose="A one-page suburb snapshot for appraisals from public sales results.",
         repo="ellar-place/suburb-reports", hosting="netlify", site="sparkly-otter-4f21ab", database=None,
         ai=None, users=40, dns="suburbs", tables=[]),
    dict(key="lease-renewal", name="Lease renewal reminder", owner="chloe.w", kind="web",
         purpose="Emails property managers 90, 60 and 30 days before a lease ends.",
         repo="chloew/lease-renewals", hosting="firebase", project="lease-renewals-a91e", database="firestore",
         ai=None, users=26,
         tables=[("leases", ["tenant_name", "tenant_email", "property_address", "lease_end"], 2_870)]),
    dict(key="trust-matcher", name="Trust receipt matcher", owner="ruby.s", kind="script",
         purpose="A Python script that matches bank deposits to rent receipts for the trust account.",
         repo="rubys/trust-matcher", hosting=None, database=None, ai=None, users=2,
         tables=[]),
    dict(key="entry-photos", name="Entry condition photos", owner="sophie.q", kind="web",
         purpose="Property managers upload entry condition photos room by room.",
         repo="sophieq/entry-photos", hosting="firebase", project="entry-photos-3b0d", database="firestore",
         ai=None, users=31,
         tables=[("inspections", ["tenant_name", "property_address", "room", "photo_url", "taken_at"], 22_600)]),
    dict(key="staff-roster", name="Weekend roster", owner="isla.c", kind="web",
         purpose="Who covers open homes and phones on weekends.",
         repo="islac/weekend-roster", hosting="netlify", site="weekend-roster", database="supabase", ref="elsnqvwtrkpzmxcb",
         ai=None, users=3,
         tables=[("shifts", ["staff_name", "staff_mobile", "shift_date", "office"], 1_240)]),
    dict(key="marketing-budget", name="Marketing budget tracker", owner="hugo.n", kind="web",
         purpose="Vendor-paid advertising spend against the agreed budget, per campaign.",
         repo="hugon/marketing-budget", hosting="netlify", site="mkt-budget-tracker", database="supabase", ref="fmtrqzxwvkpldnye",
         ai=None, users=15,
         tables=[("campaigns", ["vendor_name", "property_address", "budget_cents", "spent_cents"], 690)]),
    dict(key="settlement-tracker", name="Settlement date tracker", owner="liam.d", kind="web",
         purpose="Contract dates, finance and building-and-pest deadlines, and settlement.",
         repo="liamd/settlements", hosting="netlify", site="settlements", database="supabase", ref="gnwsrxqzyvlmpakf",
         ai=None, users=38,
         tables=[("contracts", ["buyer_name", "vendor_name", "property_address", "finance_date", "settlement_date", "price_cents"], 1_530)]),
    dict(key="referrals", name="Referral tracker", owner="max.f", kind="web",
         purpose="Referrals from past clients and who is owed a thank-you.",
         repo="maxf/referrals", hosting="firebase", project="referrals-c2e8", database="firestore",
         ai=None, users=0,
         tables=[("referrals", ["referrer_name", "referrer_email", "lead_name", "lead_phone"], 310)]),
    dict(key="call-list", name="Prospecting call list", owner="jack.t", kind="web",
         purpose="A daily list of past appraisal contacts to call.",
         repo="jackt/call-list", hosting="netlify", site="call-list", database="supabase", ref="hpxtszqwyvmrnbkl",
         ai=None, users=19,
         tables=[("contacts", ["contact_name", "contact_phone", "property_address", "last_called"], 9_870)]),
    dict(key="cma-helper", name="Comparable sales helper", owner="theo.v", kind="web",
         purpose="Pulls recent comparable sales for an appraisal.",
         repo="theov/cma-helper", hosting="netlify", site="cma-helper", database=None,
         ai=None, users=24, tables=[]),
    dict(key="smoke-alarms", name="Smoke alarm compliance tracker", owner="aria.l", kind="web",
         purpose="Which rentals have compliant smoke alarms and when the next check is due.",
         repo="arial/smoke-alarms", hosting="netlify", site="smoke-alarms", database="supabase", ref="jqyvutzwxmnrlpcd",
         ai=None, users=21,
         tables=[("properties", ["property_address", "tenant_phone", "alarm_checked_at", "next_due"], 4_120)]),
    dict(key="rental-applications", name="Rental application checker", owner="zoe.m", kind="web",
         purpose="Applicants upload ID and payslips; the leasing team ranks applications.",
         repo="zoem/rental-apps", hosting="firebase", project="rental-apps-5d77", database="firestore",
         ai="anthropic_api", users=27,
         tables=[("applications", ["applicant_name", "applicant_email", "date_of_birth", "licence_no", "id_document_url", "income_cents", "payslip_url"], 3_460)]),
    dict(key="policy-agent", name="Policy Q and A agent", owner="lucy.e", kind="agent",
         purpose="Answers staff questions from the policy handbook on SharePoint.",
         agent_id="cs-policy-0042", connectors=["SharePoint"], ai="copilot_studio", users=140, tables=[]),
    dict(key="onboarding-agent", name="Onboarding checklist agent", owner="lucy.e", kind="agent",
         purpose="Walks a new starter through their first-week checklist.",
         agent_id="cs-onboard-0077", connectors=["SharePoint", "Microsoft Teams"], ai="copilot_studio", users=23, tables=[]),
    dict(key="price-scraper", name="Listing price history scraper", owner="ben.y", kind="script",
         purpose="A Python script that saves listing price changes from public portals each night.",
         repo="beny/price-history", hosting=None, database=None, ai=None, users=1, tables=[]),
    dict(key="feedback-summariser", name="Open home feedback summariser", owner="leo.h", kind="web",
         purpose="Summarises buyer feedback from open homes for the vendor report.",
         repo="leoh/feedback-summary", hosting="netlify", site="feedback-summary", database=None,
         ai="openai_personal", users=33, tables=[]),
    dict(key="fee-calc", name="Management fee calculator", owner="ivy.g", kind="web",
         purpose="Quotes management fees for landlords.",
         repo="ivyg/fee-calc", hosting="netlify", site="fee-calc", database=None, ai=None, users=17, tables=[]),
    dict(key="leaderboard", name="Agent leaderboard", owner="ben.y", kind="web",
         purpose="Listings, sales and appraisals by agent, month to date.",
         repo="beny/leaderboard", hosting="netlify", site="leaderboard", database="supabase", ref="kvzqmtxwplsynrbe",
         ai=None, users=96,
         tables=[("results", ["agent_name", "listings", "sales", "appraisals", "month"], 2_200)]),
    dict(key="signature-gen", name="Email signature generator", owner="hugo.n", kind="web",
         purpose="Makes a consistent email signature for new staff.",
         repo="hugon/signatures", hosting="netlify", site="signatures", database=None, ai=None, users=11, tables=[]),
    dict(key="brochure-helper", name="Brochure layout helper", owner="ella.r", kind="web",
         purpose="Lays out a print brochure from a listing.",
         repo="ellar-place/brochure", hosting="netlify", site="brochure-helper", database=None, ai=None, users=8, tables=[]),
    dict(key="vacate-checklist", name="Tenant vacate checklist", owner="sophie.q", kind="web",
         purpose="What a tenant must do before the final inspection, sent by link.",
         repo="sophieq/vacate", hosting="firebase", project="vacate-checklist-11fa", database="firestore",
         ai=None, users=14,
         tables=[("vacates", ["tenant_name", "tenant_email", "property_address", "vacate_date"], 1_090)]),
    dict(key="bond-tracker", name="Bond lodgement tracker", owner="mia.k", kind="web",
         purpose="Bonds received and whether each has been lodged on time.",
         repo="miak/bond-tracker", hosting="netlify", site="bond-tracker", database="supabase", ref="lwrqtzmvxkpnsyda",
         ai=None, users=12,
         tables=[("bonds", ["tenant_name", "tenant_email", "property_address", "bond_amount_cents", "account_bsb", "account_no", "lodged_at"], 2_610)]),
    dict(key="route-planner", name="Inspection route planner", owner="sophie.q", kind="web",
         purpose="Orders a day's routine inspections into a driving route.",
         repo="sophieq/route-planner", hosting="netlify", site="route-planner", database=None, ai=None, users=16, tables=[]),
    dict(key="leads-agent", name="Leads inbox summariser", owner="finn.a", kind="agent",
         purpose="A Copilot Studio agent that summarises the overnight leads inbox for each agent.",
         agent_id="cs-leads-0310", connectors=["Office 365 Outlook", "Dropbox (personal)"], ai="copilot_studio", users=25, tables=[]),
    dict(key="vendor-portal", name="Vendor portal prototype", owner="oscar.p", kind="web",
         purpose="A prototype where vendors log in to see their campaign.",
         repo="oscarp/vendor-portal", hosting="netlify", site="vendor-portal-proto", database="supabase", ref="mzxtqrwvylpkbnse",
         ai=None, users=6,
         tables=[("vendors", ["vendor_name", "vendor_email", "vendor_phone", "property_address"], 380)]),
    dict(key="water-splitter", name="Water invoice splitter", owner="ivy.g", kind="script",
         purpose="A Python script that splits water invoices between owner and tenant.",
         repo="ivyg/water-split", hosting=None, database=None, ai=None, users=3, tables=[]),
    dict(key="auction-results", name="Auction results recorder", owner="max.f", kind="web",
         purpose="Records auction results on the day for the weekend report.",
         repo="maxf/auction-results", hosting="firebase", project="auction-results-8d03", database="firestore",
         ai=None, users=20,
         tables=[("results", ["listing_address", "suburb", "result", "sale_price_cents", "auction_date"], 1_760)]),
    dict(key="birthday-bot", name="Team birthday bot", owner="lucy.e", kind="agent",
         purpose="Posts birthdays in each office's Teams channel.",
         agent_id="cs-bday-0008", connectors=["Microsoft Teams"], ai="copilot_studio", users=0, tables=[]),
    dict(key="spring-microsite", name="Spring campaign microsite", owner="hugo.n", kind="web",
         purpose="A microsite for a past seasonal campaign.",
         repo="hugon/spring-campaign", hosting="netlify", site="spring-campaign-2025", database=None, ai=None, users=0, tables=[]),
    dict(key="arrears-dashboard", name="Arrears dashboard", owner="sophie.q", kind="web",
         purpose="Tenants in arrears by property manager; built at another office.",
         repo="sophieq/arrears-dash", hosting="firebase", project="arrears-dash-0c4b", database="firestore",
         ai=None, users=7,
         tables=[("arrears", ["tenant_name", "tenant_email", "property_address", "arrears_cents"], 640)]),
    dict(key="my-first-app", name="my-first-app", owner="ben.y", kind="web",
         purpose="A Supabase tutorial project, never used for work.",
         repo="beny/my-first-app", hosting=None, database="supabase", ref="nqzrwxvmtkpylsde",
         ai=None, users=0, tables=[("todos", ["title", "done"], 4)]),
]

TOOL_KEYS = [t["key"] for t in TOOLS]

# ---- Seeded defects -------------------------------------------------------
# Each is placed into the exports or the code by the generator, and each must
# be found from them. key -> what was seeded.
SEEDED = {
    # The owner has left (HR feed) but the tool still has users.
    "orphaned": ["lease-renewal", "smoke-alarms", "auction-results"],
    # A live credential in the repository.
    "secret_in_repo": ["appraisal-writer", "arrears", "trust-matcher", "feedback-summariser"],
    # A key that bypasses the database's access rules, shipped to the browser.
    "service_key_in_client": ["vendor-portal", "buyer-followup"],
    # Anyone on the internet can read or write the personal data.
    "open_data_rules": ["open-home", "rental-applications", "bond-tracker"],
    # Open read rules on data that is public anyway: not a finding.
    "open_rules_public_data": ["auction-results"],
    # SQL assembled from request input.
    "sql_from_input": ["leaderboard", "settlement-tracker"],
    # A serverless function that answers without checking who is asking.
    "unauthenticated_function": ["vendor-report", "marketing-budget"],
    # Personal data sent straight to a model API on a personal key, not
    # through the approved gateway.
    "personal_data_to_unapproved_ai": ["appraisal-writer", "appraisal-gen", "rental-applications", "feedback-summariser"],
    # The same route with public listing data only: held, to move behind the gateway.
    "model_call_outside_gateway_public_data": ["listing-copy", "social-scheduler"],
    # A Copilot Studio agent with a connector to personal storage.
    "agent_personal_connector": ["maintenance-agent", "leads-agent"],
    # A dependency that does not exist in the registry (a name a model made up).
    "nonexistent_package": ["listing-copy", "suburb-report"],
    # A dependency version under a (synthetic) advisory.
    "vulnerable_dependency": ["commission-calc", "cma-helper", "route-planner"],
    # Personal data written to logs.
    "personal_data_in_logs": ["open-home", "call-list"],
    # A key-shaped string in a test fixture: hold for a person, do not refuse.
    "key_shaped_test_fixture": ["fee-calc"],
    # Removed from the code, still in the history, never rotated.
    "secret_in_history_only": ["signature-gen"],
    # Two tools doing one job.
    "duplicate_pairs": [("appraisal-writer", "appraisal-gen"), ("arrears", "arrears-dashboard")],
    # Billed but nobody used it in 30 days.
    "idle": ["spring-microsite", "my-first-app", "referrals"],
    # A paid plan far bigger than the use.
    "oversized_plan": ["key-register", "staff-roster"],
    # Hosting site name unlike the repository's; joined by key regardless.
    "renamed_site": ["suburb-report", "marketing-budget", "vendor-portal"],
}

# Discovery rows that cannot be matched to one tool. Held, never guessed.
HELD = {
    # Paid on an expense claim; no matching resource in any export.
    "expense_without_resource": [("ella.r", "Bubble"), ("finn.a", "Glide")],
    # Two repositories both deploy the same site.
    "two_repos_one_site": [("leoh/vendor-report-old", "vendor-report")],
}

# DNS records that point at a hosting site that no longer exists: anyone who
# registers that site name receives the traffic.
DANGLING_DNS = [("listings-old", "listings-old-2024.netlify.app"), ("promo", "promo-winter.web.app")]

# Azure sandbox: resources Terraform declares, and three made by hand.
AZURE_DECLARED = ["rg-place-sandbox", "cae-place-sandbox", "log-place-sandbox", "st-place-sandbox-tfstate"]
# (name, type, A$ cents a month)
AZURE_UNDECLARED = [("vm-test-claude", "Virtual machine B2s", 6_210), ("pg-flex-trial", "PostgreSQL flexible server B1ms", 3_480),
                    ("ai-search-poc", "AI Search basic", 11_240)]

# Synthetic security advisories: package, vulnerable below this version.
ADVISORIES = [
    ("ADV-SYN-0001", "markdown-it-lite", "4.2.0", "high", "Script injection through link titles."),
    ("ADV-SYN-0002", "jsonwebtoken-mini", "2.0.3", "critical", "Accepts unsigned tokens."),
    ("ADV-SYN-0003", "csv-quickparse", "1.8.0", "moderate", "Formula injection in exported cells."),
]
# The registry the gate checks package names against (a snapshot, synthetic).
REGISTRY_SNAPSHOT = [
    "react", "react-dom", "vite", "@supabase/supabase-js", "firebase", "firebase-admin", "@anthropic-ai/sdk", "openai",
    "date-fns", "zod", "express", "axios", "chart.js", "tailwindcss", "markdown-it-lite", "jsonwebtoken-mini", "csv-quickparse",
    "@netlify/functions", "papaparse", "leaflet", "pdf-lib", "dayjs", "uuid", "lodash", "requests", "pandas", "openpyxl",
]

# The approved route for model calls: the gateway Place would run (an
# assumption of the design, named in the AI policy). Anything else holding
# personal data is refused.
APPROVED_AI_HOSTS = ["ai-gateway.place-tools.example"]
APPROVED_AI_TOOLS = {
    # tool in the AI register -> (approved, data allowed)
    "Microsoft Copilot Studio": (True, "internal and personal, inside the tenant"),
    "GitHub Copilot": (True, "code only"),
    "Claude Code": (True, "code only"),
    "Anthropic API via the AI gateway": (True, "internal and personal, logged and masked"),
    "Anthropic API, direct with a personal key": (False, "none"),
    "OpenAI API, direct with a personal key": (False, "none"),
    "Azure OpenAI (sandbox)": (True, "synthetic and internal only until reviewed"),
}

# Tools nobody declared in the inventory survey; found only in the exports.
UNDECLARED = ["lease-renewal", "smoke-alarms", "auction-results", "referrals", "my-first-app", "spring-microsite"]

# The process each declared tool supports, as the builder picked it in the
# survey. Two tools on one process is a duplicate to look at.
PROCESS = {
    "appraisal-writer": "Appraisals", "appraisal-gen": "Appraisals", "listing-copy": "Listing marketing",
    "open-home": "Open homes", "arrears": "Rent arrears", "arrears-dashboard": "Rent arrears",
    "vendor-report": "Vendor reporting", "commission-calc": "Commissions", "key-register": "Keys",
    "maintenance-agent": "Maintenance", "buyer-followup": "Buyer follow-up", "social-scheduler": "Social media",
    "suburb-report": "Market reports", "trust-matcher": "Trust accounting", "entry-photos": "Inspections",
    "staff-roster": "Rostering", "marketing-budget": "Vendor-paid advertising", "settlement-tracker": "Contracts and settlement",
    "call-list": "Prospecting", "cma-helper": "Comparable sales", "rental-applications": "Tenant selection",
    "policy-agent": "Staff knowledge", "onboarding-agent": "Onboarding", "price-scraper": "Market data",
    "feedback-summariser": "Open home feedback", "fee-calc": "Landlord quotes", "leaderboard": "Sales reporting",
    "signature-gen": "Brand", "brochure-helper": "Print marketing", "vacate-checklist": "Vacates",
    "bond-tracker": "Bonds", "route-planner": "Routine inspections", "leads-agent": "Leads",
    "vendor-portal": "Vendor portal", "water-splitter": "Utilities recovery", "birthday-bot": "Culture",
}

# Billing months in the cost history.
BILLING_MONTHS = ["2026-05", "2026-06", "2026-07", "2026-08", "2026-09", "2026-10"]

# ---- Monitoring -------------------------------------------------------------
ALERT_START = datetime(2026, 10, 19, 0, 0, 0)
ALERT_DAYS = 28
MONITORED = ["listing-copy", "open-home", "vendor-report", "commission-calc", "appraisal-writer", "leaderboard",
             "settlement-tracker", "rental-applications", "call-list", "suburb-report"]
# The nightly deploy and restart window for every monitored app.
MAINTENANCE = (2, 0, 2, 20)  # 02:00 to 02:20

# The real incidents in the four weeks. id -> (tool, start offset hours, category)
INCIDENTS = {
    "INC-01": ("vendor-report", 3 * 24 + 10, "bad_deploy"),
    "INC-02": ("appraisal-writer", 6 * 24 + 8, "expired_secret"),
    "INC-03": ("listing-copy", 9 * 24 + 14, "upstream_outage"),
    "INC-04": ("leaderboard", 13 * 24 + 9, "quota_exhausted"),
    "INC-05": ("settlement-tracker", 16 * 24 + 11, "db_connection_exhaustion"),
    "INC-06": ("suburb-report", 20 * 24 + 7, "cert_expiry"),
    "INC-07": ("appraisal-writer", 24 * 24 + 15, "runaway_cost"),
}
# Noise seeded into the alert stream.
NOISE = {
    "flapping_probe": "open-home",          # one probe region times out every few minutes for two days
    "duplicate_monitor": "commission-calc",  # the same check configured in two monitors
    "cold_start_latency": "call-list",       # first request after idle is slow every morning
    "busy_but_fine": "commission-calc",      # month-end run: slow for twenty minutes, no errors
}
NOISE_BUSY_DAY = 12
