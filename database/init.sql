CREATE TABLE IF NOT EXISTS tenders (
    id SERIAL PRIMARY KEY,
    code TEXT NOT NULL UNIQUE,
    title_mn TEXT NOT NULL,
    purpose_mn TEXT NOT NULL,
    owner_unit TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('active', 'completed', 'archived')),
    stage TEXT NOT NULL CHECK (stage IN ('registration', 'rule_check', 'human_review', 'approved')),
    budget_mnt NUMERIC(18, 2) NOT NULL,
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
    status TEXT NOT NULL DEFAULT 'received',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS tender_findings (
    id SERIAL PRIMARY KEY,
    tender_id INTEGER NOT NULL REFERENCES tenders(id) ON DELETE CASCADE,
    submission_id INTEGER REFERENCES tender_submissions(id) ON DELETE CASCADE,
    category TEXT NOT NULL,
    severity TEXT NOT NULL CHECK (severity IN ('attention', 'information')),
    message_mn TEXT NOT NULL,
    source_reference TEXT NOT NULL,
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
    approval_note TEXT,
    source_snapshot JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    approved_at TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS audit_events (
    id SERIAL PRIMARY KEY,
    tender_id INTEGER REFERENCES tenders(id) ON DELETE SET NULL,
    event_type TEXT NOT NULL,
    actor TEXT NOT NULL,
    details JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

INSERT INTO tenders (
    id, code, title_mn, purpose_mn, owner_unit, status, stage, budget_mnt, due_date
)
VALUES (
    1,
    'БШУЯ-2026-014',
    'Сургуулийн дижитал сургалтын төхөөрөмж нийлүүлэх',
    'Ерөнхий боловсролын сургуулиудад багш, сурагчийн хэрэглээнд зориулсан төхөөрөмж нийлүүлэх жишиг худалдан авалт.',
    'Боловсролын яам · Худалдан авах ажиллагааны нэгж',
    'active',
    'human_review',
    1200000000,
    CURRENT_DATE + INTERVAL '14 days'
)
ON CONFLICT (id) DO NOTHING;

INSERT INTO tender_submissions (
    id, tender_id, organization_name, proposed_amount_mnt,
    documents_complete, tax_compliant, technical_score, status
)
VALUES
    (1, 1, 'Жишээ Технологи ХХК', 1080000000, TRUE, TRUE, 84.50, 'reviewed'),
    (2, 1, 'Ирээдүй Системс ХХК', 1145000000, FALSE, TRUE, 88.00, 'needs_information'),
    (3, 1, 'Нээлттэй Дижитал ХХК', 1230000000, TRUE, TRUE, 81.25, 'reviewed')
ON CONFLICT (id) DO NOTHING;

INSERT INTO tender_findings (
    id, tender_id, submission_id, category, severity, message_mn, source_reference
)
VALUES
    (
        1, 1, 2, 'document_completeness', 'attention',
        'Баталгаат засвар үйлчилгээний хавсралт бүрэн ирээгүй байна.',
        'Submission 2 · Document checklist · Item 7'
    ),
    (
        2, 1, 3, 'budget_check', 'attention',
        'Санал болгосон үнэ батлагдсан төсвөөс 30,000,000 төгрөгөөр давсан байна.',
        'Submission 3 · Financial proposal · Total amount'
    ),
    (
        3, 1, 1, 'tax_compliance', 'information',
        'Татварын тодорхойлолт хүчинтэй гэж бүртгэгдсэн.',
        'Submission 1 · Tax certificate · Verified field'
    )
ON CONFLICT (id) DO NOTHING;

INSERT INTO audit_events (id, tender_id, event_type, actor, details)
VALUES (
    1,
    1,
    'rule_check_completed',
    'system',
    '{"rules_checked": 5, "attention_findings": 2}'::jsonb
)
ON CONFLICT (id) DO NOTHING;

SELECT setval('tenders_id_seq', GREATEST((SELECT MAX(id) FROM tenders), 1));
SELECT setval('tender_submissions_id_seq', GREATEST((SELECT MAX(id) FROM tender_submissions), 1));
SELECT setval('tender_findings_id_seq', GREATEST((SELECT MAX(id) FROM tender_findings), 1));
SELECT setval('audit_events_id_seq', GREATEST((SELECT MAX(id) FROM audit_events), 1));
