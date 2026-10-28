"""Remove titles that swallowed the text after them (an unclosed quote in the program).

Usage: python -I src/clean_titles.py <db_path>
  paper titles longer than 260 characters are dropped (a real title is rarely over 200);
  a session title longer than 250 characters that contains a closing quote is cut at it
  (1998's G.1 ran into the presenters' names).
Run after every parser so a fix in one place cannot be undone by a later rebuild.
"""
import sqlite3, sys

def main(db_path):
    con = sqlite3.connect(db_path)
    n = con.execute("UPDATE appearance SET paper_title = NULL WHERE length(paper_title) > 260").rowcount
    m = 0
    for sid, title in con.execute("SELECT id, title FROM session WHERE length(title) > 250").fetchall():
        for q in ('"', "”"):
            if q in title:
                con.execute("UPDATE session SET title = ? WHERE id = ?", (title.split(q)[0].strip(), sid)); m += 1
                break
    con.commit()
    print(f"clean_titles: {n} paper titles dropped, {m} session titles cut")

if __name__ == "__main__":
    main(sys.argv[1])
