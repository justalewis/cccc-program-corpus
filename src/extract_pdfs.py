"""Extract the captured program PDFs from the capture WARCs into a folder.

Usage: python -I src/extract_pdfs.py <capture_dir> <out_dir>
File names keep the path below /convention/, /uploads/ or (Wayback) /cccc/, with '/' replaced by '__'.
"""
import glob, os, sys
from warcio.archiveiterator import ArchiveIterator

def main(capture_dir, out):
    os.makedirs(out, exist_ok=True)
    n = 0
    for warc in glob.glob(os.path.join(capture_dir, "*.warc.gz")):
        if "eshow" in warc:
            continue
        with open(warc, "rb") as f:
            for rec in ArchiveIterator(f):
                if rec.rec_type != "response" or rec.http_headers.get_statuscode() != "200":
                    continue
                url = rec.rec_headers.get_header("WARC-Target-URI")
                if not url.lower().endswith(".pdf"):
                    continue
                if "/convention/" in url:
                    name = url.split("/convention/")[-1]
                elif "/uploads/" in url:
                    name = url.split("/uploads/")[-1]
                else:  # Wayback replay of www.ncte.org/cccc/99/program/a.pdf
                    name = url.split("/cccc/")[-1]
                with open(os.path.join(out, name.replace("/", "__")), "wb") as o:
                    o.write(rec.content_stream().read())
                n += 1
    print(f"extracted {n} PDFs")

if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
