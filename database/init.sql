-- Organization Brain Starter - demonstration schema and sample data.
--
-- IMPORTANT: every organization, official, bidder, amount and document
-- reference below is FICTIONAL. The data exists only to demonstrate the
-- workflow. It does not describe any real ministry, agency, company or
-- procurement process, and it must never be used for an official decision.
--
-- Design notes (English, for developers):
--   * This file holds FACTS only. Rule results are NOT stored here; they are
--     computed in apps/api/app/rules.py from these facts on every request, so
--     a reviewer can always recompute them by hand from the same rows.
--   * AI output is stored in `decisions` and is always created with
--     status = 'draft'. Only an explicit human approval action changes it.
--   * `audit_events` records action, actor, actor role, target and metadata.

CREATE TABLE IF NOT EXISTS tenders (
    id SERIAL PRIMARY KEY,
    code TEXT NOT NULL UNIQUE,
    title_mn TEXT NOT NULL,
    purpose_mn TEXT NOT NULL,
    owner_unit TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('active', 'completed', 'archived')),
    stage TEXT NOT NULL CHECK (stage IN ('registration', 'rule_check', 'human_review', 'approved')),
    budget_mnt NUMERIC(18, 2) NOT NULL,
    -- Rule thresholds live with the tender so the checks stay data-driven
    -- and auditable instead of being hidden inside application code.
    min_technical_score NUMERIC(5, 2) NOT NULL DEFAULT 0,
    min_bidders INTEGER NOT NULL DEFAULT 1,
    due_date DATE NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS tender_submissions (
    id SERIAL PRIMARY KEY,
    tender_id INTEGER NOT NULL REFERENCES tenders(id) ON DELETE CASCADE,
    organization_name TEXT NOT NULL,
    proposed_amount_mnt NUMERIC(18, 2) NOT NULL,
    documents_complete BOOLEAN NOT NULL DEFAULT FALSE,
    tax_compliant BOOLEAN NOT NULL DEFAULT FALSE,
    technical_score NUMERIC(5, 2),
    -- Free-text pointer to the paper or scanned record the facts came from.
    evidence_reference TEXT NOT NULL DEFAULT 'Demonstration record',
    status TEXT NOT NULL DEFAULT 'received',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS decisions (
    id SERIAL PRIMARY KEY,
    tender_id INTEGER NOT NULL REFERENCES tenders(id) ON DELETE CASCADE,
    decision_type TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('draft', 'approved', 'rejected')),
    content_mn TEXT NOT NULL,
    generated_by TEXT NOT NULL,
    approved_by TEXT,
    approved_by_role TEXT,
    approval_note TEXT,
    -- Exact structured facts and rule results the draft was based on.
    source_snapshot JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    approved_at TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS audit_events (
    id SERIAL PRIMARY KEY,
    tender_id INTEGER REFERENCES tenders(id) ON DELETE SET NULL,
    event_type TEXT NOT NULL,
    actor TEXT NOT NULL,
    actor_role TEXT,
    target TEXT,
    details JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_submissions_tender ON tender_submissions (tender_id);
CREATE INDEX IF NOT EXISTS idx_decisions_tender ON decisions (tender_id);
CREATE INDEX IF NOT EXISTS idx_audit_tender ON audit_events (tender_id, created_at DESC);

COMMENT ON TABLE tenders IS 'FICTIONAL demonstration data. Not a real procurement record.';
COMMENT ON TABLE tender_submissions IS 'FICTIONAL demonstration data. Not a real bid.';

-- ---------------------------------------------------------------------------
-- Fictional sample data
-- ---------------------------------------------------------------------------

INSERT INTO tenders (
    id, code, title_mn, purpose_mn, owner_unit, status, stage,
    budget_mnt, min_technical_score, min_bidders, due_date
)
VALUES (
    1,
    'ЖИШЭЭ-2026-014',
    'Сургуулийн дижитал тоног төхөөрөмж нийлүүлэх',
    'Жишээ байгууллагын сургуулиудад багш, сурагчийн хэрэглээнд зориулсан тоног төхөөрөмж нийлүүлэх зохиомол жишиг худалдан авалт.',
    'Жишээ байгууллага · Худалдан авах ажиллагааны алба',
    'active',
    'human_review',
    1200000000,
    80.00,
    3,
    CURRENT_DATE + INTERVAL '14 days'
)
ON CONFLICT (id) DO NOTHING;

INSERT INTO tender_submissions (
    id, tender_id, organization_name, proposed_amount_mnt,
    documents_complete, tax_compliant, technical_score, evidence_reference, status
)
VALUES
    (1, 1, 'Жишээ-А Технологи ХХК', 1080000000, TRUE, TRUE, 84.50,
     'Материалын хавтас №1 · 2026-07-28', 'reviewed'),
    (2, 1, 'Жишээ-Б Системс ХХК', 1145000000, FALSE, TRUE, 88.00,
     'Материалын хавтас №2 · 2026-07-28', 'needs_information'),
    (3, 1, 'Жишээ-В Дижитал ХХК', 1230000000, TRUE, TRUE, 78.00,
     'Материалын хавтас №3 · 2026-07-29', 'reviewed')
ON CONFLICT (id) DO NOTHING;

INSERT INTO audit_events (id, tender_id, event_type, actor, actor_role, target, details)
VALUES (
    1,
    1,
    'tender_registered',
    'system',
    'system',
    'tender:1',
    '{"note": "Fictional demonstration tender created by database seed."}'::jsonb
)
ON CONFLICT (id) DO NOTHING;

SELECT setval('tenders_id_seq', GREATEST((SELECT MAX(id) FROM tenders), 1));
SELECT setval('tender_submissions_id_seq', GREATEST((SELECT MAX(id) FROM tender_submissions), 1));
SELECT setval('decisions_id_seq', GREATEST((SELECT COALESCE(MAX(id), 0) FROM decisions), 1));
SELECT setval('audit_events_id_seq', GREATEST((SELECT MAX(id) FROM audit_events), 1));
