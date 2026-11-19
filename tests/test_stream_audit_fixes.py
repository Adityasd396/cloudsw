import tempfile,subprocess,sys,shutil,os
from pathlib import Path
import unittest
from unittest.mock import patch
import test_app
from app import app,db

class PollLockTests(unittest.TestCase):
    setUp=test_app.WatchPartyTests.setUp
    tearDown=test_app.WatchPartyTests.tearDown
    def test_frequent_room_poll_does_not_acquire_a_writer_for_noop_heartbeat(self):
        with app.app_context():
            statements=[];db().set_trace_callback(statements.append)
            self.host.get(self.url);self.host.get(self.url)
            self.assertFalse(any(q.startswith('UPDATE members SET seen') for q in statements),statements)
    def test_stale_heartbeat_still_refreshes_presence(self):
        import time
        with app.app_context():
            db().execute('UPDATE members SET seen=?',(time.time()-10,));db().commit()
        self.host.get(self.url)
        with app.app_context():self.assertGreater(db().execute("SELECT seen FROM members WHERE name='Host'").fetchone()[0],time.time()-2)
    def test_game_get_uses_read_transaction_and_mutations_keep_write_lock(self):
        for kind in ['game','basketball','ludo']:
            with app.app_context():
                statements=[];db().set_trace_callback(statements.append)
                self.assertEqual(self.host.get(self.url+'/'+kind).status_code,200)
                self.assertIn('BEGIN',statements);self.assertNotIn('BEGIN IMMEDIATE',statements)
                statements.clear();self.assertEqual(self.host.post(self.url+'/'+kind,json={'action':'join'}).status_code,200)
                self.assertIn('BEGIN IMMEDIATE',statements)

class ContainerManifestTests(unittest.TestCase):
    def test_docker_copy_list_can_import_the_real_application(self):
        root=Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory(prefix='solace-container-fixture-') as folder:
            target=Path(folder)
            for line in (root/'Dockerfile').read_text().splitlines():
                if line.startswith('COPY ') and line.endswith(' ./'):
                    for name in line.split()[1:-1]:shutil.copyfile(root/name,target/name)
            for name in ['templates','static']:shutil.copytree(root/name,target/name,ignore=shutil.ignore_patterns('media'))
            result=subprocess.run([sys.executable,'-B','-c',"from app import app; c=app.test_client(); assert c.get('/api/health').status_code==200; assert c.get('/').status_code==200"],cwd=folder,env={**os.environ,'SECRET_KEY':'disposable-container-test'},capture_output=True,text=True,timeout=30)
            self.assertEqual(result.returncode,0,result.stderr)
