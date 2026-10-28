# Deploying a usable version

Recommendation, 28 October 2026. Nothing has been deployed.

## Recommendation: two stages

### Stage 1, now: a private Datasette instance on Fly.io

The corpus is one read-only SQLite file of about 30 MB. Datasette serves a file like that with no application code. It gives:

- browsing, full-text search and faceting on every table
- CSV and JSON for any view
- saved ("canned") queries
- custom page templates that can become the year, person and institution pages in `tools-and-interface.md`

Charts come from plugins: `datasette-vega` or `datasette-plot` for trends, and `datasette-cluster-map` for the map once the IPEDS coordinates are copied in.

Why Fly.io:

- `datasette publish fly` (the `datasette-publish-fly` plugin) packages the database and deploys it with one command.
- The Fly account from Pinakes's first host already exists.
- A small machine that stops when idle costs a few dollars a month at most.

Keep it private until the rights question is settled. Either add the `datasette-auth-passwords` plugin, or put Cloudflare Access in front, since the Cloudflare account is already in use. Deploy the **release** SQLite (`build/release/.../cccc-program-corpus.sqlite`), which has no session descriptions and no eShow keys, not `build/corpus.db`.

Sketch (to run once Justin approves):

```
pip install datasette datasette-publish-fly datasette-auth-passwords datasette-vega
datasette publish fly build/release/cccc-program-corpus-v0.1.0-draft/cccc-program-corpus.sqlite \
  --app cccc-program-corpus -m metadata.yml \
  --install datasette-auth-passwords --install datasette-vega \
  --plugin-secret datasette-auth-passwords root_password_hash '<hash>'
```

### Stage 2, when it goes public: inside Pinakes

Pinakes already plans person and institution pages, and the corpus's people should link to their articles there. So the public version belongs in the Pinakes Flask app at pinakes.wacclearinghouse.org, reading the release SQLite.

Files can't be copied from this machine to the Clearinghouse server. Two ways in:

1. The server downloads the release zip from Zenodo by its DOI.
2. It pulls from git.

Both avoid copying files by hand. A Datasette instance can stay up beside Pinakes as the "query the data" view, linked from the Pinakes pages.

## Alternatives considered

- **Static site from the SQLite file** (pages generated at build time, or Datasette Lite loading the file in the browser). There's no server, so hosting on Cloudflare Pages is free. But it's public by default, and every change means a rebuild. It works well for Stage 2's public face, and less well for a private working copy.
- **A custom app now.** Too early. The interface isn't designed, and NCTE hasn't been asked about the descriptions yet.
- **The Clearinghouse server for Stage 1.** It adds a deploy path that has to be pasted by hand, and it puts unpublished data on someone else's server.

## Before anything public

- Decide the data license (CC0 or CC BY 4.0) and whether to notify or ask NCTE.
- Keep session descriptions out until NCTE agrees.
- Have a corrections route for listed people (the release README has a placeholder).
