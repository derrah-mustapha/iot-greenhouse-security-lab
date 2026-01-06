"""q.py 'SQL' : run a query on the readings DB, print tab-separated rows."""
import sqlite3, sys
db = sqlite3.connect("/data/readings.db")
for row in db.execute(sys.argv[1]):
    print("\t".join("" if v is None else str(v) for v in row))
