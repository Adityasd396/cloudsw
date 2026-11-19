import sqlite3,tempfile,time,unittest
from pathlib import Path
from contextlib import closing
from tools.maintenance import cleanup

class RetentionTests(unittest.TestCase):
    def test_cleanup_keeps_account_history_and_only_expires_old_operational_data(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder);now=time.time()
            with closing(sqlite3.connect(path/'afterglow.db')) as c:
                c.executescript("CREATE TABLE accounts(id TEXT); INSERT INTO accounts VALUES('account'); CREATE TABLE watch_history(id INTEGER,owner TEXT,last REAL); CREATE TABLE watch_people(entry INTEGER); CREATE TABLE watch_slices(entry INTEGER); CREATE TABLE account_tokens(expires REAL);")
                c.executemany('INSERT INTO watch_history VALUES(?,?,?)',[(1,'guest',now-31*86400),(2,'account',now-31*86400),(3,'guest',now)])
                c.executemany('INSERT INTO watch_people VALUES(?)',[(1,),(2,),(3,)]);c.execute('INSERT INTO account_tokens VALUES(0)');c.commit()
            with closing(sqlite3.connect(path/'solace-admin.db')) as c:c.execute('CREATE TABLE events(created REAL)');c.executemany('INSERT INTO events VALUES(?)',[(now,),(now-31*86400,)]);c.commit()
            result=cleanup(path,now);self.assertEqual(result['guest_history'],1);self.assertEqual(result['events'],1)
            with closing(sqlite3.connect(path/'afterglow.db')) as c:self.assertEqual(c.execute('SELECT id FROM watch_history ORDER BY id').fetchall(),[(2,),(3,)]);self.assertEqual(c.execute('SELECT entry FROM watch_people ORDER BY entry').fetchall(),[(2,),(3,)])
