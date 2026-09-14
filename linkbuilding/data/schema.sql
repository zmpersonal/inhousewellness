-- InHouse Wellness link building — the spine.
-- Every pipeline is a function that moves rows between states.

CREATE TABLE IF NOT EXISTS targets (
    id                INTEGER PRIMARY KEY,
    domain            TEXT NOT NULL,
    url               TEXT,

    -- source|dealer|gap|resource_page|roundup|mention|citation
    tactic            TEXT NOT NULL,
    discovered_via    TEXT,
    discovered_at     TEXT NOT NULL,

    -- metrics
    dr                INTEGER,
    referring_domains INTEGER,
    organic_traffic   INTEGER,
    spam_score        INTEGER,

    -- scoring (see 04_qualify)
    relevance         INTEGER,   -- 0-40
    authority         INTEGER,   -- 0-25
    traffic_reality   INTEGER,   -- 0-15
    link_likelihood   INTEGER,   -- 0-20
    risk_flags        TEXT,      -- JSON array; any entry = auto-reject
    composite_score   INTEGER,

    -- new|qualified|rejected|queued|drafted|sent|responded|live|dead
    status            TEXT NOT NULL DEFAULT 'new',

    contact_name      TEXT,
    contact_email     TEXT,
    contact_source    TEXT,

    sent_at           TEXT,
    live_url          TEXT,
    anchor_text       TEXT,
    anchor_class      TEXT,      -- brand|naked_url|generic|exact_match
    rel_attr          TEXT,
    last_checked      TEXT,
    notes             TEXT
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_targets_domain_tactic ON targets(domain, tactic);
CREATE INDEX IF NOT EXISTS idx_targets_status ON targets(status);
CREATE INDEX IF NOT EXISTS idx_targets_score  ON targets(composite_score DESC);

-- Journalist requests. Separate table: these expire, targets don't.
CREATE TABLE IF NOT EXISTS requests (
    id             INTEGER PRIMARY KEY,
    platform       TEXT NOT NULL,   -- sos|haro|qwoted|featured|journorequest
    outlet         TEXT,
    outlet_dr      INTEGER,
    query_text     TEXT NOT NULL,
    deadline       TEXT,
    ingested_at    TEXT NOT NULL,
    topic_match    TEXT,            -- JSON array of matched filter terms
    priority       INTEGER,         -- outlet_dr weighted against time remaining
    -- new|filtered_out|drafted|routed|sent|published|no_response
    status         TEXT NOT NULL DEFAULT 'new',
    draft          TEXT,
    routed_to      TEXT,
    published_url  TEXT,
    got_link       INTEGER          -- 0/1; some quotes publish without a link
);

CREATE INDEX IF NOT EXISTS idx_requests_status ON requests(status);
CREATE INDEX IF NOT EXISTS idx_requests_priority ON requests(priority DESC);

-- Velocity guard. 07_verify writes here; nothing is queued past the cap.
CREATE TABLE IF NOT EXISTS placements (
    id            INTEGER PRIMARY KEY,
    target_id     INTEGER REFERENCES targets(id),
    week_of       TEXT NOT NULL,   -- ISO week start
    anchor_text   TEXT,
    anchor_class  TEXT,
    landed_at     TEXT
);

CREATE INDEX IF NOT EXISTS idx_placements_week ON placements(week_of);
