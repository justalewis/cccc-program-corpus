# What the program corpus can show: tools and an interface

Status, 28 October 2026. No public interface has been designed yet. The corpus has a local Datasette view (`datasette build/corpus.db -m metadata.yml`), two private review pages, and the plan page. This note lists what the extracted data can support, so the interface can be designed around it.

## What the data holds

| Field | Years | Notes |
|---|---|---|
| Session code and title | 1998, 1999, 2004–2027 | 16,064 sessions; titles for all but 36 |
| Proposal area | 2025 and 2026 per session (eShow `tracks`); PDF years only as a front-matter "Selected Topic Guide" index | The PDFs do not tag each session with an area. They print a topic guide near the front that lists session codes under topic headings (10–16 a year, renamed over time), and that index still has to be parsed. 1999 has no guide. |
| eShow tracks (proposal areas) | 2025, 2026 | 17–21 areas, e.g. "First-Year Writing," "Antiracism and Social Justice" |
| Session type | eShow years, 2024–2027 | Panel, individual presentation, roundtable, workshop, poster, SIG, Engaged Learning Experience |
| Audience level | 2024 only | Two-year, four-year, graduate |
| Session description | 2024–2027 | 2,446 sessions; NCTE's text, kept private until NCTE agrees |
| Role | all years | Chair, speaker, respondent, workshop leader, roundtable leader, discussion leader; spellings vary and need folding |
| Name and affiliation as printed | all years | 63,325 appearances |
| Paper title | about half of appearances | 31,397 appearances |
| Person cluster | all years | Exact-name clusters: 20,637 names, with 3,555 joined as job moves and 317 waiting on review |
| Institution | 97% of appearances that print an affiliation | ROR id and country; US colleges carry IPEDS sector, level, Carnegie class and the two-year flag. The same IPEDS file also has control, state, county, latitude and longitude, and HBCU and tribal-college flags, which aren't copied in yet |
| Day, time, room | eShow years | Rooms and times only; no attendance |
| Convention city, status | 1949–2027 | Held, cancelled (2020), virtual (2021, 2022), upcoming (2027) |
| Theme, program chair | 1950–2025 | On NCTE's past-conventions page; not loaded yet |
| Call for proposals text | none yet | Would need its own harvest (cccc.ncte.org and the Wayback Machine, and *CCC* for the print years) |

Everything counts people **listed in the program**, not registrants or attendees.

## Tools the data can support

Each entry gives what the tool shows, what it needs, and whether the data is ready now.

### Topics

1. **Topic-area trends.** Share of sessions in each proposal area by year: Basic Writing, Writing Programs, Information Technologies, and so on. Needs the topic guides parsed and a crosswalk across renamed areas (2005's "Practices of Teaching Writing" becomes 2013's "Teaching Writing & Rhetoric" and 2019's "Writing Pedagogies and Processes"). *Ready after one parser change plus a hand-built crosswalk.*
2. **Term trends in titles.** How often a word or phrase appears in session and paper titles by year ("multimodal," "translingual," "antiracist," "AI," "labor," "transfer"), as raw counts and as a share of titles. Works on titles alone. *Ready now.*
3. **Term search with context.** Type a term and see the titles that use it, grouped by year, with links to the sessions. *Ready now.*
4. **Emerging and fading terms.** Words whose share rose or fell most between two periods, with the first year each appears. *Ready now*, with the caveat that 2000–2003 is missing.
5. **Topic models or embedding clusters** over titles (and over descriptions for 2024–2027, privately). Finds groupings the official areas miss. *Possible now*; the clusters need a person to name and check them before anything is public.
6. **Area by institution type.** Which proposal areas two-year faculty, graduate students (where identifiable) or HBCU faculty present in. Needs the topic labels. *After item 1.*

### People and careers

7. **Person page.** Every listed appearance for one person: year, role, session, title, institution at the time. *Ready now* for exact-name clusters; better after the near-match review.
8. **Career arcs.** First appearance, last appearance, number of conventions, and the move from speaker to chair to respondent. *Ready now.*
9. **Cohorts and retention.** Of the people first listed in a given year, how many come back in later years, broken out by institution type. *Ready now*; sensitive to name matching, so it should carry a caveat.
10. **Role patterns.** Who chairs, who responds, and how that changes by institution type or over time. Needs role spellings folded into a few categories. *Small step.*
11. **Institution moves.** People's movement between institutions as the program records it: from R1s to regional comprehensives, two-year to four-year, and so on. *Ready now* for clusters already joined as moves.

### Institutions and access

12. **Institution page.** Every appearance from one college by year, its type, and the people listed. *Ready now.*
13. **Two-year share and other institution-type shares by year.** The chart on the plan page, extended to Carnegie class, public and private control, HBCUs and tribal colleges, and countries outside the US. *Ready now* for Carnegie class and country; *small step* for the rest (copy four more IPEDS columns).
14. **Map.** Where listed people come from each year, using IPEDS coordinates and ROR's location for colleges outside the US, with the host city marked. *Small step* (copy the IPEDS coordinates in).
15. **Host-city effect.** Whether nearby institutions show up more when the convention is close: share of people within a set distance of the host city, by year. *After the map step.* (The repeated cities, San Francisco in 2005 and 2009 and Chicago in 1998, 2006 and 2023, make a natural comparison.)
16. **Concentration.** How much of each program comes from the top 10 or 50 institutions, and whether that has changed. *Ready now.*

### Conventions and calls

17. **Convention year page.** City, status, size, session types, top areas, institution mix, and a link to the source document. *Ready now* except theme and chair, which need loading.
18. **Year-to-year comparison.** Two years side by side: size, areas, terms, institution mix, returning people. *Ready now.*
19. **Call versus program.** The call's text and named areas next to what the program accepted: which terms from the call appear in titles that year and how often. Needs the CFP texts harvested first. *Not ready; needs a new harvest.*
20. **Theme echo.** How often the convention theme's words show up in that year's titles. Needs themes loaded. *Small step.*
21. **Format change over time.** The rise of roundtables, posters, workshops and Engaged Learning Experiences, and the virtual years. Full detail only for 2024–2027; for the PDF years, session codes and role labels give a rougher picture. *Partly ready.*

### Networks

22. **Co-presentation network.** People linked by sharing a session, by year or across years. *Ready now*; the clearest version uses only reviewed clusters.
23. **Institution collaboration.** Which institutions appear on the same panels, and how often panels mix institution types (for example, two-year and four-year faculty together). *Ready now.*

### Links to publication (with Pinakes)

24. **From presentation to article.** Papers given at CCCC that later appear in a journal indexed in Pinakes, matched by person and title similarity, with each link marked suggested or confirmed. *Needs Pinakes data* (an export, since the server isn't reachable from this machine).
25. **Lag and venue.** Time from convention paper to article, and which journals take them. *After item 24.*

### Utility

26. **Search across everything:** names, institutions, titles, years.
27. **Downloads:** CSV for any view, with the counting caveats attached.
28. **Corrections:** a way for a listed person to flag a wrong match or ask to be merged or split, which the plan already requires for name changes.

## Interface sketch

The natural home is Pinakes, which already plans person and institution pages. A first version could be a set of pages generated from the SQLite file:

- **Year page** (items 17, 13, 1, 2): one per convention, the default landing spot.
- **Session page:** code, title, people, institutions, source page.
- **Person page** (7, 8) and **institution page** (12).
- **Trends explorer** (1, 2, 4, 13, 21): one chart area with a measure picker (topic area, term, institution type, format), a year range, and the caveat line always shown.
- **Compare** (18, 19): two years, or a call and its program.
- **Map** (14, 15).

Datasette with a few custom pages would work as a private prototype before anything goes into Pinakes.

## Limits every chart has to show

- People are counted as **listed in the program**, not as attendees.
- 2000–2003 is missing, and the print years (1949–1997) aren't in yet.
- The source changes from PDF to eShow at 2024, so a step between 2023 and 2024 may be the source, not the field.
- 2020 is the program of a cancelled convention; 2021 and 2022 were virtual.
- Person counts rest on exact-name clustering plus review.
- Session descriptions stay private until NCTE agrees.

## Suggested order

1. Parse the PDF topic guides, add eShow tracks, and build the area crosswalk (unlocks items 1, 6, 17).
2. Copy the remaining IPEDS columns: control, state, coordinates, HBCU and tribal flags (13, 14, 15).
3. Load themes and chairs from NCTE's past-conventions page (17, 20).
4. Fold role spellings into a few categories (10).
5. Prototype the year page and trends explorer in Datasette.
6. Harvest CFP texts (19).
7. Pinakes links once there's an export (24, 25).
