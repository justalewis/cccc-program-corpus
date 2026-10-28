# Linking convention papers to Pinakes: plan and pilot

Status, 28 October 2026. A pilot matcher runs (`src/link_pinakes.py`). Nothing is published, and no link is confirmed.

## What this adds

The program says who was put on the stage. Pinakes says what the field published. A link between them answers questions neither corpus can alone: how many convention papers reach print, how long it takes, where they land, and whether that differs by area or by kind of institution. It also lets a reader go from a session to the article it became, and from an article to the convention where it was first presented.

## What I need from Justin: nothing to export

Pinakes already serves everything the match needs at its public API (`/api/articles`, 200 records a request). The WPA-L reader pulled a dump of it yesterday: 67,281 works with id, DOI, title, authors, publication date, journal and citation counts, saved at `../wpa-l-archive/data/reference/pinakes/works.jsonl`. The pilot ran on that file. For later phases the API also returns abstracts, tags, keywords and an OpenAlex id, which I'd fetch with the same polite loop (one request a second, about six minutes for everything). No Pinakes code changes.

## How the match works

For each listed paper title (31,721 appearances have one), the matcher looks for articles whose title shares most of its distinctive words, published from one year before the convention to eight years after. It scores three kinds of evidence:

- **Title:** overlap of distinctive words, and whether the part before a colon is identical.
- **Author:** the presenting name's last name and first initial appear among the article's authors.
- **Time:** the article's year against the convention year.

Tiers: **A** near-identical title and an author match; **B** a close title and an author match; **C** an author match and a partly overlapping title; **D** a near-identical title with no author match.

## What the pilot found

| Tier | Suggested links | What I saw in a sample of seven |
|---|---|---|
| A | 201 | All plausible. Several are the same title word for word ("Resisting the Fixity of Suburban Space," Robert Topinka, 2011 and then *Rhetoric Society Quarterly*, 2012). |
| B | 76 | Mostly right. Some are co-authored panels where both authors match the same article. |
| C | 181 | Mixed. Some are plausible reworkings ("Tools Matter," 2014 and then *Written Communication*, 2018). Some need a person to decide. |
| D | 152 | Mostly wrong: a common title, a different author. Dropped from the plan. |

- **Lag:** among tiers A and B, 25 articles appeared the year before the convention, 67 the same year, 80 the next year, 56 two years later, and a tail out to eight. The median is one year.
- **Where they land:** *College Composition and Communication* (31), *Teaching English in the Two-Year College* (26), *Computers and Composition* (19), *Enculturation* (17), *Composition Forum* (15), *Pedagogy* (14), *College English* (12).
- **People:** about 32% of the 19,006 people with a first and last name appear as an author in Pinakes under the same first and last name. It's 53% for people listed at two or more conventions, 17% for people listed once, and 25% for people at two-year colleges against 33% at other institutions. These are name matches, so common names inflate them and name variants lower them. Treat them as a preview of what the measure would show, not as findings.

Only about 0.6% of titled papers (201 of 31,721) land in tier A. That is a floor, not an estimate of how many papers reach print:

1. Pinakes indexes journals, and many conference papers become book chapters or appear in journals it doesn't cover.
2. Titles change between the program and the article.
3. About half of all listings carry no paper title, so panels and many workshops can't be matched by title.
4. The matcher is deliberately strict.

## Plan

1. **Review, then decide.** I build a review page like the others: the 257 tier B and C pairs, plus a random 150 from tier A to measure precision. The page shows the paper title and presenter beside the article, with Same / Different / Not sure. Tier A is the only tier I'd show publicly before review, as "may later appear as," with a badge.
2. **Loosen where it's safe.** Add matches on session titles for individual-presentation formats (2024 on), on titles with a subtitle dropped, and on abstract text (see the decision below). Each addition is measured against the reviewed pairs before it joins the pool.
3. **Store it.** Reviewed and tier A links go in the existing `link` table (`session_id`, `person_id`, `pinakes:<id>`, method, score, status suggested, confirmed or rejected) and in the release as `links.csv`. Rejected pairs are kept so a rebuild doesn't suggest them again.
4. **Reader pages.**
   - **Session page:** "May later appear as," with the article and a link to its Pinakes page.
   - **Person page:** convention papers that reached print.
   - **Talk to text:** the share of titled papers that reached print by year, area and institution type, with the lag and the venues.
   - **Presenting and publishing:** the share of listed people with any Pinakes article, as aggregates only.
5. **A reverse link for Pinakes.** If you want article pages in Pinakes to say "presented at CCCC 2013," the interface is one CSV (`pinakes_id`, convention year, session code, reader URL). Pinakes would ingest it the way it ingests other data. Pinakes stays untouched until you decide.
6. **Later: author identity.** OpenAlex author ids and ORCID (via each article's DOI) would give a stronger person-to-author match than a name, and would let a person claim their own record.

## Decisions for Justin

1. **Public display of tier A before review?** I'd show it as "likely" with a badge. The alternative is waiting for the review pass.
2. **May I use NCTE's session descriptions (2024–2027, private) to score matches?** The text would stay private. Only the resulting link would be published. It would raise recall for the most recent years.
3. **Does the aggregate "presenting and publishing" belong on the public site?** The thresholds are groups of at least 20 and no labels on individuals, but it is the most sensitive page in the plan, since it can read as ranking institutions by who publishes.
4. **Should Pinakes get the reverse link?** It is the one piece that touches the Pinakes site.

## Limits to state wherever the links appear

- Links are suggestions made by software. Tier A is likely right; it is not confirmed.
- A missing link means no match was found, not that the paper never appeared.
- Pinakes covers a subset of journals, and no books.
- Counts of people who "also publish" use names, with the errors that implies.
