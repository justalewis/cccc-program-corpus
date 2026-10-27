"""Compare session codes in the eShow listing with session codes printed in the PDF program.

Usage: python -I src/check_pdf_codes.py <capture_dir> <db_path>
Pulls the 2024-2026 program PDFs out of the capture WARC (nothing is downloaded again).
"""
import glob, os, re, sqlite3, sys
import pymupdf
from warcio.archiveiterator import ArchiveIterator

PDFS = {2024: "2024-CCCC-Conv-Program-final-3-24.pdf", 2025: "4Cs-2025-4-6.pdf", 2026: "2026-final-CCCC-program.pdf"}
CODE = re.compile(r"^\s*([A-Z]{1,2})[.\-](\d{1,3})\b", re.M)

def pdf_bytes(capture_dir, name):
    for warc in glob.glob(os.path.join(capture_dir, "cccc-ncte-wp-content-*.warc.gz")):
        with open(warc, "rb") as f:
            for rec in ArchiveIterator(f):
                if rec.rec_type == "response" and rec.rec_headers.get_header("WARC-Target-URI").endswith("/" + name):
                    return rec.content_stream().read()

def main(capture_dir, db_path):
    con = sqlite3.connect(db_path)
    for year, name in PDFS.items():
        data = pdf_bytes(capture_dir, name)
        doc = pymupdf.open(stream=data, filetype="pdf")
        text = "\n".join(p.get_text() for p in doc)
        pdf_codes = {f"{a}.{int(n)}" for a, n in CODE.findall(text)}
        es = {re.sub(r"^([A-Z]{1,2})[.\-]0*(\d+).*$", r"\1.\2", c) for (c,) in con.execute(
            "select code from session where year=? and code is not null and parent_id is null", (year,))}
        n_es = con.execute("select count(*) from session where year=? and parent_id is null", (year,)).fetchone()[0]
        both = pdf_codes & es
        print(f"{year}: PDF pages {doc.page_count}; codes in PDF {len(pdf_codes)}; eShow sessions {n_es}, with code {len(es)}; "
              f"shared {len(both)}; PDF-only {len(pdf_codes - es)}; eShow-only {len(es - pdf_codes)}")
        print("   PDF-only sample:", sorted(pdf_codes - es)[:25])
        print("   eShow-only sample:", sorted(es - pdf_codes)[:15])

if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
