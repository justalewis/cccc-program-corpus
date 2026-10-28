"""Load the 79 conventions (1949-2027) from data/conventions.csv.

Usage: python -I src/load_conventions.py <db_path> <conventions.csv>
"""
import csv, os, sqlite3, sys

def main(db_path, csv_path):
    con = sqlite3.connect(db_path)
    con.executescript(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "schema.sql"), encoding="utf-8").read())
    rows = list(csv.DictReader(open(csv_path, encoding="utf-8")))
    for r in rows:
        con.execute("""INSERT INTO convention(year, city, status) VALUES (?,?,?)
                       ON CONFLICT(year) DO UPDATE SET city=excluded.city, status=excluded.status""",
                    (int(r["year"]), r["city"], r["status"]))
    con.commit()
    print(f"conventions: {len(rows)}")

if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
