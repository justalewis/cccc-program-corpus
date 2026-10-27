-- CCCC Program Corpus schema. Every extracted row points to the source document it came from.

CREATE TABLE IF NOT EXISTS convention (
  year        INTEGER PRIMARY KEY,
  city        TEXT,
  venue       TEXT,
  theme       TEXT,
  chair       TEXT,
  status      TEXT CHECK (status IN ('held', 'cancelled', 'virtual', 'upcoming'))
);

CREATE TABLE IF NOT EXISTS source_document (
  id            TEXT PRIMARY KEY,          -- e.g. eshow-listing-2025
  year          INTEGER REFERENCES convention(year),
  kind          TEXT,                      -- eshow-listing, eshow-detail, pdf, html, scan, journal
  url           TEXT,
  warc_file     TEXT,
  sha256        TEXT,
  captured_utc  TEXT,
  rights        TEXT
);

CREATE TABLE IF NOT EXISTS session (
  id                 TEXT PRIMARY KEY,     -- eshow:<session key>
  year               INTEGER REFERENCES convention(year),
  source_document_id TEXT REFERENCES source_document(id),
  parent_id          TEXT REFERENCES session(id),  -- child presentations in a combined panel
  code               TEXT,                 -- as printed: L.7, B.32 ...
  title              TEXT,
  session_type       TEXT,                 -- Concurrent Panel, Workshop, Poster ... (Presentation for a child)
  audience_level     TEXT,                 -- 2024 only: Two-year | Four-year | Graduate level
  tracks             TEXT,                 -- topic clusters and any extra type chips, ' | ' separated
  dates              TEXT,                 -- ' | ' separated when a session runs several days
  time_label         TEXT,                 -- 11:00 AM - 12:15 PM EDT
  room               TEXT,
  room_level         TEXT,
  cancelled          INTEGER DEFAULT 0,
  description        TEXT,                 -- from the detail view; private until NCTE agrees
  eshow_key          TEXT
);

CREATE TABLE IF NOT EXISTS appearance (
  id                     INTEGER PRIMARY KEY,
  session_id             TEXT REFERENCES session(id),
  ord                    INTEGER,
  role                   TEXT,             -- label printed before the name, e.g. Speaker(s), Workshop Leader
  name_as_printed        TEXT,
  affiliation_as_printed TEXT,
  eshow_person_key       TEXT,
  person_id              TEXT REFERENCES person(id),
  institution_id         TEXT REFERENCES institution(id),
  source_document_id     TEXT REFERENCES source_document(id)
);

CREATE TABLE IF NOT EXISTS person (
  id            TEXT PRIMARY KEY,
  display_name  TEXT,
  orcid         TEXT,
  openalex_id   TEXT,
  pinakes_id    TEXT,
  method        TEXT                       -- how the cluster was formed
);

CREATE TABLE IF NOT EXISTS institution (
  id              TEXT PRIMARY KEY,        -- ROR id where matched, else local:<slug>
  name            TEXT,
  ror_id          TEXT,
  wikidata        TEXT,
  ipeds_unitid    TEXT,
  sector          INTEGER,                 -- IPEDS SECTOR
  iclevel         INTEGER,                 -- IPEDS ICLEVEL: 1 four-year+, 2 two-year, 3 less than two-year
  two_year        INTEGER,
  carnegie_basic  INTEGER,                 -- IPEDS C21BASIC
  country         TEXT,
  kind            TEXT                     -- ROR type: education, company, nonprofit ...
);

CREATE TABLE IF NOT EXISTS affiliation_match (
  affiliation_as_printed TEXT PRIMARY KEY,
  institution_id         TEXT REFERENCES institution(id),
  method                 TEXT,             -- ror-affiliation-chosen, ror-affiliation-top, manual, none
  score                  REAL
);

CREATE TABLE IF NOT EXISTS link (
  id            INTEGER PRIMARY KEY,
  session_id    TEXT REFERENCES session(id),
  person_id     TEXT REFERENCES person(id),
  target        TEXT,                      -- pinakes:<id> or openalex:<id>
  method        TEXT,
  score         REAL,
  status        TEXT CHECK (status IN ('suggested', 'confirmed', 'rejected'))
);

CREATE INDEX IF NOT EXISTS ix_app_session ON appearance(session_id);
CREATE INDEX IF NOT EXISTS ix_app_person ON appearance(eshow_person_key);
CREATE INDEX IF NOT EXISTS ix_app_aff ON appearance(affiliation_as_printed);
CREATE INDEX IF NOT EXISTS ix_session_year ON session(year);
