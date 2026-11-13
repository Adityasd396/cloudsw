"""Smoke actual app import/schema setup, without the manually built test fixture."""
import os
from pathlib import Path
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import time
import unittest

ROOT=Path(__file__).resolve().parents[1]


class StartupSmokeTests(unittest.TestCase):
    def verify_startup(self,legacy=False):
        temporary=tempfile.TemporaryDirectory(prefix='.smoke-startup-',dir=ROOT)
        target=Path(temporary.name).resolve()
        self.assertEqual(target.parent,ROOT.resolve())
        try:
            for name in ('app.py','room_game.py','admin_panel.py'):shutil.copy2(ROOT/name,target/name)
            shutil.copytree(ROOT/'templates',target/'templates')
            if legacy:
                (target/'instance').mkdir()
                connection=sqlite3.connect(target/'instance'/'afterglow.db')
                try:
                    connection.executescript('''
                    CREATE TABLE rooms(id TEXT PRIMARY KEY,name TEXT,host TEXT,video TEXT,playing INTEGER DEFAULT 0,position REAL DEFAULT 0,updated REAL);
                    CREATE TABLE members(room TEXT,id TEXT,name TEXT,seen REAL,PRIMARY KEY(room,id));
                    CREATE TABLE messages(id INTEGER PRIMARY KEY AUTOINCREMENT,room TEXT,name TEXT,body TEXT,created REAL);
                    CREATE TABLE queue(id INTEGER PRIMARY KEY AUTOINCREMENT,room TEXT,video TEXT,title TEXT,added_by TEXT);
                    ''')
                    connection.execute('INSERT INTO rooms VALUES(?,?,?,?,?,?,?)',('123456','Legacy','old-host','aqz-KE-bpKQ',0,0,time.time()))
                    connection.execute('INSERT INTO messages(room,name,body,created) VALUES(?,?,?,?)',('123456','Old name','Saved before upgrade',time.time()))
                    connection.execute('INSERT INTO queue(room,video,title,added_by) VALUES(?,?,?,?)',('123456','aqz-KE-bpKQ','Old song','Old name'))
                    connection.commit()
                finally:connection.close()
            script='''
from app import app,db
app.config['TESTING']=True
with app.app_context():
    assert {'sender','reply_to'} <= {r['name'] for r in db().execute('PRAGMA table_info(messages)')}
    assert 'playback_id' in {r['name'] for r in db().execute('PRAGMA table_info(rooms)')}
    assert 'sort_order' in {r['name'] for r in db().execute('PRAGMA table_info(queue)')}
client=app.test_client()
assert client.get('/api/health').status_code==200
assert client.get('/').status_code==200
assert client.get('/ops/solace').status_code==404
room='123456' if LEGACY else client.post('/api/rooms',json={}).json['id']
endpoint='/api/rooms/'+room
result=client.post(endpoint,json={'action':'join','name':'Startup smoke'})
assert result.status_code==200 and result.json['playback_id']
if LEGACY:
    assert result.json['messages'][0]['body']=='Saved before upgrade'
    assert result.json['queue'][0]['title']=='Old song'
    assert client.post(endpoint,json={'action':'chat','body':'Reply after upgrade','reply_to':result.json['messages'][0]['id']}).status_code==200
assert client.post(endpoint+'/game',json={'action':'join'}).status_code==200
assert client.post(endpoint,json={'action':'ad_status','active':True}).status_code==200
assert client.post(endpoint+'/leave',json={}).json['room_deleted']
assert client.get(endpoint).status_code==404
print('Fresh schema and preserved legacy data checks passed.')
'''.replace('LEGACY','True' if legacy else 'False')
            environment=os.environ.copy();environment.pop('SOLACE_ADMIN_PASSWORD_HASH',None)
            result=subprocess.run([sys.executable,'-B','-c',script],cwd=target,env=environment,text=True,capture_output=True,timeout=40)
            self.assertEqual(result.returncode,0,result.stdout+result.stderr)
        finally:temporary.cleanup()

    def test_fresh_install_starts_and_serves_rooms(self):self.verify_startup()

    def test_legacy_database_migrates_without_losing_history(self):self.verify_startup(legacy=True)


if __name__=='__main__':unittest.main()
