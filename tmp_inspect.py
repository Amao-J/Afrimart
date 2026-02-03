import sqlite3
conn=sqlite3.connect('db.sqlite3')
c=conn.cursor()
for r in c.execute("PRAGMA table_info('main_userprofile')"):
    print(r)
conn.close()
