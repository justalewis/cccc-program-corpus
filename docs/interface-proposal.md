# A research interface for the CCCC program corpus

Proposal, 28 October 2026. It builds on `tools-and-interface.md`, Pinakes's tools page, and the WPA-L Archive Reader's build spec.

## What a program is evidence of

A journal records who published. A listserv records who spoke up. A convention program records who was **admitted to the field's main stage in a given year**, and in what role, from which institution, and under which of the organization's own headings.

That record is wider than publication. The corpus lists 20,715 names. Of those, 12,107 appear at a single convention, and 2,904 appear at five or more. The single-year names include many people who never publish in the journals Pinakes indexes: two-year faculty, graduate students, contingent faculty, high-school teachers and independent scholars.

The program is also an **institutional document**. Each year's proposal areas are CCCC's own map of the field, and the map changes:

- 2005: "Practices of Teaching Writing"
- 2011: "Teaching Writing & Rhetoric"
- 2019: "Writing Pedagogies and Processes"
- 2022–2026: "Approaches to Teaching and Learning"

Special interest groups and standing groups come and go. Formats change too: the Engaged Learning Experience, the virtual years, the cancelled 2020 program.

A program is also a forecast, not a minutes book. It records what was accepted and scheduled, not who showed up. The 2020 program describes a convention that never happened. Every tool has to carry that caveat.

These features suggest three kinds of work the tooling can ground:

- **Disciplinography:** who the field is when it convenes, and how people and institutions move through it.
- **Historiography:** the program as a dated record of the organization's categories, firsts and formats, read with source criticism.
- **Trend analysis:** topics, formats and participation over time, with honest denominators.

## Design principles

These come from what already works in Pinakes and the WPA-L reader.

1. **Organize by question.** Pinakes's tools page groups its 20 tools under five questions ("How does the field cite?"). The same shape works here, and it keeps the three projects legible as siblings.
2. **Normalize, and show the break.** Raw counts mostly track how big the program was. Every trend chart shows a share (per 1,000 titles, per listed person), with the raw count one click away. Every chart also marks the corpus's breaks:
   - no data for 2000–2003
   - the source change from PDF to eShow in 2024
   - the cancelled 2020 convention
   - the virtual years, 2021 and 2022
   - the provisional 2027 listing

   The WPA-L spec makes the same point for list volume.
3. **Every number opens its rows, and every row opens its page.** A point on a chart opens the sessions behind it. A session cites its printed page, linking to NCTE's own PDF at that page (`…/2013program.pdf#page=142`), so provenance stays with NCTE's public copy rather than ours.
4. **Show how each match was made.** Person clusters and institution matches carry their method (exact name, reviewed merge, ROR, IPEDS alias, place-stripped) as a small badge, as the WPA-L reader does for rebuilt threads. Unmatched strings stay visible.
5. **A word is not a concept.** Term search needs word boundaries and a reader.
   - **Word boundaries:** "labor" matches 658 session titles as a substring but 209 as a word, because "collaboration" contains it. The current public saved query uses substring matching; it should move to word boundaries.
   - **A reader:** the first title with "translingual" (2007) is about Civil War soldiers' letters. Sessions in the field's sense of the word begin in 2011. So "first sightings" need a person to check them before anyone calls them firsts.
6. **People are colleagues.** Names in a published program are public, but derived judgments about a career are not. The ethics rules below apply to every person-level view.
7. **Make it citable.** Any filtered view can become a saved corpus with a stable URL, a build date and an export, as in WPA-L spec item 2.

## Proposed tools

**Readiness:** **Now** runs on the release data as it stands. **Step** needs a small data job (listed later). **New** needs new data or a partner corpus.

### 1. Who convenes the field?

| Tool | What it shows | Ready |
|---|---|---|
| **Convention census** | Per year: listed people, sessions, newcomers (first listing) and returners, roles, and the share from outside the US. The landing chart for the whole site. | Now |
| **Institution mix** | Shares by Carnegie class, two-year and four-year, public and private, HBCU and tribal college (IPEDS flags), and country. Hispanic-Serving Institutions need the Department of Education's eligibility list added. | Now / Step |
| **Concentration** | Share of appearances from the top 10 and top 50 institutions, and a Gini coefficient, by year. Is the program getting more or less concentrated? | Now |
| **Atlas and host-city draw** | Where listed people come from each year, with the host city marked. Includes the share within driving distance and the repeated cities (San Francisco 2005 and 2009; Chicago 1998, 2006 and 2023). | Step |

### 2. How do careers move through the convention?

| Tool | What it shows | Ready |
|---|---|---|
| **Person pages** | A career strip: years across, roles as marks (speaker, chair, respondent, workshop leader), institutions as color. Plus co-panelists, linked articles (Pinakes) and WPA-L presence. Name variants and the match method are shown. | Now (strip) / New (links) |
| **Role ladder** | How people move from speaker to chair to respondent, and how long it takes by institution type. Of 17,610 people whose first listing isn't as a chair, 2,502 later chair a session. Chairing and responding are the program's gatekeeping and mentoring positions. | Step (fold role spellings) |
| **Cohorts and persistence** | People grouped by first year, with the share who return 1, 3 and 5 years later, broken out by institution type. Do two-year faculty come back at the rates others do? Shown as aggregates only. | Now |
| **Institutional flows** | Moves between institution types as the program records them: doctoral university to regional comprehensive, two-year to four-year. Doctoral institutions at first listing work as a rough feeder map for graduate programs. | Now |

### 3. What does the field talk about?

| Tool | What it shows | Ready |
|---|---|---|
| **Area trends** | Share of sessions in each proposal area by year, using CCCC's own headings. | Built (draft crosswalk), at /areas |
| **Taxonomy history** | The areas themselves as a lineage chart: when each heading appears, is renamed, splits, merges or retires. This is the organization's changing self-description, and probably the most original historiographic view the corpus offers. | Step |
| **Term trajectories** | Up to six words or phrases per 1,000 titles, by year, with the breaks marked and click-through to the titles. Same interface as WPA-L's trends page, so a term can be read across both corpora. | Now (word-boundary search needs an FTS or regex step) |
| **Firsts ledger** | The first sessions to use a term in the field's sense, with each entry checked by a person and annotated. A historiography tool that also corrects the trend chart's naive first point. | Step (review queue) |
| **Topic map over titles** | Embedding clusters or a dynamic topic model over 16,000 session titles and 31,000 paper titles. It finds groupings the official areas miss. The model version and seed are published, and topics are hand-labeled. | New (offline pipeline) |
| **Area by institution type** | A heatmap of which areas each institution type presents in. Where do two-year faculty's sessions sit on CCCC's own map? | Step |

### 4. How is the convention made?

| Tool | What it shows | Ready |
|---|---|---|
| **Program anatomy** | Formats (panels, individual presentations, roundtables, workshops, posters, SIG meetings, Engaged Learning Experiences), session size and sessions per day. It shows how the event's form changed, including the virtual years. | Now (2024–27 in full; PDF years roughly) |
| **SIG and standing-group register** | Every special interest group and standing group by name and year: births, renamings, endings. The PDFs code SIG sessions as FSIG and TSIG with 19–29 each a year from 2005 to 2017, and eShow gives them their own session type. This is a history of the field's caucuses and identity groups. | Step (extract SIG names) |
| **Call and program** | Each year's call for proposals and theme next to what was accepted. Theme echo (how often the theme's words show up in titles) and the areas the call named against the areas the program used. | New (harvest calls; load themes) |
| **Chairs and themes timeline** | Program chairs and themes, 1950–2027, as a strip the other charts can overlay. | Step (NCTE's past-conventions page) |

### 5. Who works with whom?

| Tool | What it shows | Ready |
|---|---|---|
| **Panel network by era** | People linked by sharing a session, in five-year windows, with community detection. The same network vocabulary as Pinakes's co-authorship view. | Now |
| **Bridges** | Panels that mix institution types (two-year with doctoral, US with international) and the people who most often build them. | Now |
| **Recurring teams** | Groups who present together across several conventions. These are the convention's lasting collaborations, comparable to Pinakes's co-authorship partnerships. | Now |

### 6. Where does the work go? (with Pinakes and WPA-L)

| Tool | What it shows | Ready |
|---|---|---|
| **Talk to text** | Convention papers that later appear as articles in Pinakes, matched by person and title similarity and marked suggested or confirmed. Shows the share of papers that reach print, the lag, and the venues, by area and institution type. | New (Pinakes data) |
| **Presenting and publishing** | The share of listed people with any Pinakes article, by institution type and year. It measures how much of the field convenes without publishing in the indexed journals. Aggregates only: no person is labeled as unpublished. | New |
| **Cited later** | Whether presenters' later articles are cited, and how soon. | New |
| **WPA-L crossover and a shared calendar** | CCCC dates as events on the WPA-L reader's timeline and trends (its spec item 11). Also the overlap between convention presenters and list posters, in aggregate. | New (shared IDs) |

### 7. The researcher's desk

| Tool | What it shows | Ready |
|---|---|---|
| **Corpus builder** | Save any filter or search as a named corpus with a stable URL, build date, CSV and JSON export, and a citation. | Now |
| **Citation strings** | MLA and APA citations for a program entry ("Paper presented at…"), with the page reference. | Now |
| **"How to read this year"** | A source panel on every year: what the source is, what's missing (1999 sections E, F, K and M; 2018's unlabeled areas), parser accuracy, and links to NCTE's files. | Now |
| **Corrections and claims** | Listed people can request a merge, split or correction, or claim their record with ORCID (Pinakes already has ORCID sign-in). Decisions feed the same files the review pages write. | Step |
| **API and data** | The Datasette instance stays as the open query layer behind the reader. | Now (live) |

## Page types

Each page type is a sibling of the Pinakes and WPA-L pages and uses the same Alexandrian Suite design system:

- **Year page:** the program as a document. Includes a day-by-session-block grid, areas with counts, formats, a census strip (people, newcomers, institution mix), the chair and theme, and the "How to read this year" panel. This is the default landing page for most visitors.
- **Session page:** code, title, area, format, people with roles and institutions, paper titles, and a citation linked to the printed page.
- **Person page:** the career strip, variants and match method, co-panelists, institutions, and cross-links to Pinakes and WPA-L.
- **Institution page:** listings by year, people, areas, and Carnegie and IPEDS facts.
- **Area page:** one proposal area's lineage, share over time, and representative sessions.
- **Term page:** the trajectory, the firsts entry, and matching titles by year.
- **Compare:** two years, two areas, or two institution types side by side.
- **Atlas:** the map by year.

The sidebar groups the tools under the seven questions above, as Pinakes's capsa does.

## Shared infrastructure across the three projects

- **A person registry.** One ID per person across the CCCC corpus, Pinakes authors and WPA-L posters, with every name variant mapped to it and ORCID where someone has claimed it. Each project already builds clusters and review queues. Sharing the IDs is what turns three corpora into one disciplinography.
- **Institution IDs.** ROR and IPEDS, which the corpus and the WPA-L reader both already use.
- **One event calendar.** Conventions, call deadlines, position statements and list events, kept as a CSV that all three projects read.
- **One design system and one ethics page**, so the three projects make the same promises.

## Ethics

The programs are public, but this corpus aggregates them into something the programs never were: a career record of living colleagues.

- **No evaluative labels on people.** No "left the field," no "never published," no ranks of individuals. Those measures exist only as aggregates.
- **Thresholds.** Network views show people with at least three listings and edges with at least two shared sessions. Cohort and publishing measures show only groups of 20 or more.
- **No demographic inference.** No guessing gender, race or ethnicity from names, as the plan already commits.
- **Corrections and opt-out.** Anyone listed can ask to have their person page suppressed. Their rows stay in the program-level counts, because the program printed them, but no page gathers them.
- **NCTE's text stays out.** Session descriptions stay out until NCTE agrees.
- **An `/ethics` page** that explains all of this.

## Data work the tools need

| Job | Unlocks | Size |
|---|---|---|
| Done: proposal areas read from the italic line above each session (2004–2017, 2019–2026), matched by code; 2018's hashtags kept as tags; draft family crosswalk. Still to do: a second reader for the crosswalk, and the SIG register | Area trends, taxonomy history, area by institution type, year pages | Small now |
| Fold role spellings into about six roles | Role ladder, person strips | Small |
| Extract SIG and standing-group names | SIG register | Small to medium |
| Copy IPEDS control, state, coordinates, HBCU and tribal flags; add HSI eligibility | Institution mix, atlas | Small |
| Load themes and chairs from NCTE's past-conventions page | Chairs and themes, year pages, theme echo | Small |
| Word-boundary term search (FTS5 tokens, or a regex function) | Term trajectories, firsts | Small |
| Harvest calls for proposals (cccc.ncte.org, Wayback, *CCC*) | Call and program | Medium |
| Pinakes author and article matching, and shared person IDs | All of section 6, person cross-links | Medium; needs a Pinakes export |
| Topic model pipeline | Topic map | Medium |
| The print years (UIUC scans, 1949–1997) | Extends every tool back to the first convention | Large; waits on the archive emails |

## Build sequence and architecture

Build it as a Flask app on the WPA-L reader's pattern: Jinja templates, the Alexandrian Suite, aggregates precomputed at build time, and deployment on Fly. It reads the release SQLite. Datasette stays live as the data and API layer. When Pinakes is ready for it, the reader moves under pinakes.wacclearinghouse.org or links from it.

1. **Foundation:**
   - year, session, person and institution pages
   - the census, term trajectories with word boundaries, and the corpus builder
   - "How to read this year"
   - the ethics page

   Data jobs first: labels, roles, IPEDS columns, themes.
2. **The program's own categories:** area trends, taxonomy history, the SIG register, program anatomy, and the chairs and themes timeline.
3. **Careers and networks:** role ladder, cohorts, institutional flows, panel network, bridges and recurring teams.
4. **Across corpora:** the person registry, talk to text, presenting and publishing, the WPA-L calendar, and the firsts ledger.
5. **Calls and print years** as those sources arrive.

## Questions for Justin

1. **Standalone or Pinakes?** Should the reader start as its own site (like the WPA-L reader) or as a section of Pinakes from the start?
2. **Ethics thresholds:** are the person-level and cohort thresholds above the right ones? Should the opt-out be suppress-the-page or remove-the-rows?
3. **Which question leads?** Which of the seven questions should the first public version lead with? My suggestion is "Who convenes the field?", with the census and the year pages, since that's where the program says something the journals can't.
