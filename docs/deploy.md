# Deploying the public view

## What is running

A public Datasette instance on Fly.io, app `cccc-program-corpus` (region `sjc`), at https://cccc-program-corpus.fly.dev. Justin chose public access with no login on 28 October 2026.

It serves the **release** database, not `build/corpus.db`. The release has no session descriptions and no eShow keys. On top of the release, `src/deploy_db.py` adds:

- full-text search on session titles, names, affiliations, paper titles and institution names
- indexes on the join columns
- a `year_summary` table

`deploy/metadata.yml` holds the caveats shown on every page and four saved queries:

- a term in titles, by year
- every listing for a name
- an institution's listings by year
- the most-listed institutions in a year

The machine stops when idle and starts on the next request, so the first page after a quiet spell takes a few seconds.

## Redeploying

```
python -I src/release.py build/corpus.db build/stats.json build/release <version>
bash deploy/deploy.sh <version>
```

`deploy/deploy.sh` builds the database and `metadata.json` into `build/flyapp/`, copies in `deploy/Dockerfile` and `deploy/fly.toml`, and runs `flyctl deploy`. Datasette's cookie-signing secret is a Fly secret (`DATASETTE_SECRET`), set once, and is not in the repository.

## The reader

A second Fly app, `cccc-program-reader` (https://cccc-program-reader.fly.dev), is the research interface: the census, year, session, person and institution pages, term trends and the corpus builder. It is a separate tool from Pinakes. It is a small Flask app (`reader/`) over `reader.db`, which `reader/build_reader.py` derives from the release SQLite. Redeploy with `bash reader/deploy.sh <version>` after rebuilding the release. Person pages exist only for people listed at two or more conventions, and `data/suppressed_people.csv` lists people whose pages are removed. The reader sends `X-Robots-Tag: noindex` on every page.

## Later: inside Pinakes

Pinakes plans person and institution pages, and the corpus's people should link to their articles there. So the fuller public interface belongs in the Pinakes Flask app at pinakes.wacclearinghouse.org, reading the release SQLite.

Files can't be copied from this machine to the Clearinghouse server, so the server would either:

1. download the release zip from Zenodo by DOI, or
2. pull from git.

The Datasette instance can stay up beside it as the "query the data" view.

## Alternatives considered

- **A static site** (pages generated at build time, or Datasette Lite loading the file in the browser). There's no server, and Cloudflare Pages hosts it free. A good fit for a later public face; every change means a rebuild.
- **A custom app now.** Too early. The interface in `tools-and-interface.md` isn't designed yet.
- **The Clearinghouse server now.** Its deploy path has to be pasted by hand.

## Still open

- The data license (CC0 or CC BY 4.0) and the code license. Until a license is chosen, the default is all rights reserved.
- Whether to notify or ask NCTE.
- A corrections route. For now the site points to the repository's issues.
