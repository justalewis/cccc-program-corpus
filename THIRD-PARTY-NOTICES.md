# Third-party notices

The code in this repository is MIT licensed (`LICENSE`) and the data is CC BY 4.0 (`DATA-LICENSE.txt`). These files in `reader/static/` and `data/` come from elsewhere and keep their own licenses.

## Bundled in the repository

| File | What it is | License |
|---|---|---|
| `reader/static/chart.umd.min.js` | Chart.js 4.4.1, for the charts | MIT, Chart.js contributors, https://www.chartjs.org |
| `reader/static/us-states-10m.json` | US state outlines (us-atlas 3.0.1, `states-10m.json`), derived from US Census Bureau cartographic boundary files | ISC, Mike Bostock; the Census Bureau boundaries are in the public domain |
| `reader/static/fonts/*.woff2` | GFS Didot (Greek Font Society), Literata (TypeTogether, for Google), EB Garamond (Georg Duffner and Octavio Pardo), Atkinson Hyperlegible (Braille Institute of America) | SIL Open Font License 1.1, https://openfontlicense.org |
| `reader/static/tokens.css`, `fonts.css` | The Alexandrian Suite design tokens, copied from Eunomia's Labors and Pinakes | Justin Lewis, MIT |
| `data/wikidata_ror_ipeds.csv` | A crosswalk from ROR identifiers to IPEDS unit ids, built from Wikidata property P1771 | CC0, Wikidata |

## Used but not included

- **IPEDS** (National Center for Education Statistics, public domain) and **ROR** (CC0) data are read at build time. The IPEDS files are downloaded separately and are not in the repository.
- **PyMuPDF**, used by the build scripts to read the program PDFs, is licensed AGPL-3.0 or commercially by Artifex. It is installed separately and is not part of this repository, so anyone who distributes a combined work that includes it takes on its terms.
- **Flask**, **Datasette**, **Waitress**, **warcio**, **Beautiful Soup** and the other Python packages listed in `reader/requirements.txt` and the build scripts are installed separately under their own licenses.

## Not included, by design

NCTE's program PDFs, eShow pages, call-for-proposals text and session descriptions. They are NCTE's, and the private capture they came from is not in this repository.
