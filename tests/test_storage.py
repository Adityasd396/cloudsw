import json
from contextlib import closing
from pathlib import Path
import sqlite3
import tempfile
import time
import unittest
from tools.storage import backup,restore,verify,prune

class StorageSafetyTests(unittest.TestCase):
    def test_restored_backup_revokes_account_sessions_and_email_links(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);instance=root/'instance';instance.mkdir()
            with closing(sqlite3.connect(instance/'afterglow.db')) as connection:
                connection.executescript("CREATE TABLE account_sessions(token TEXT); INSERT INTO account_sessions VALUES('old'); CREATE TABLE account_tokens(token TEXT); INSERT INTO account_tokens VALUES('old-link'); CREATE TABLE profiles(name TEXT); INSERT INTO profiles VALUES('Saved profile'); CREATE TABLE world_presence(owner TEXT); INSERT INTO world_presence VALUES('temporary-lease'); CREATE TABLE user_preferences(world_choice TEXT); INSERT INTO user_preferences VALUES('skipped'); CREATE TABLE world_messages(body TEXT); INSERT INTO world_messages VALUES('Saved community message');");connection.commit()
            backup(instance,root/'backup');restore(root/'backup',root/'restored')
            with closing(sqlite3.connect(root/'restored/afterglow.db')) as connection:
                self.assertEqual(connection.execute('SELECT count(*) FROM account_sessions').fetchone()[0],0)
                self.assertEqual(connection.execute('SELECT count(*) FROM account_tokens').fetchone()[0],0)
                self.assertEqual(connection.execute('SELECT name FROM profiles').fetchone()[0],'Saved profile')
                self.assertEqual(connection.execute('SELECT count(*) FROM world_presence').fetchone()[0],0)
                self.assertEqual(connection.execute('SELECT world_choice FROM user_preferences').fetchone()[0],'skipped')
                self.assertEqual(connection.execute('SELECT body FROM world_messages').fetchone()[0],'Saved community message')
    def test_restore_revokes_native_handoffs_private_links_and_pending_invitations(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);instance=root/'instance';instance.mkdir()
            with closing(sqlite3.connect(instance/'afterglow.db')) as connection:
                connection.executescript("CREATE TABLE native_handoffs(token TEXT); INSERT INTO native_handoffs VALUES('short-lived'); CREATE TABLE room_settings(epoch INTEGER,link_hash TEXT,link_token TEXT); INSERT INTO room_settings VALUES(2,'hash','private-link'); CREATE TABLE room_invitations(status TEXT); INSERT INTO room_invitations VALUES('pending');");connection.commit()
            backup(instance,root/'backup');restore(root/'backup',root/'restored')
            with closing(sqlite3.connect(root/'restored/afterglow.db')) as connection:
                self.assertEqual(connection.execute('SELECT COUNT(*) FROM native_handoffs').fetchone()[0],0)
                self.assertEqual(connection.execute('SELECT * FROM room_settings').fetchone(),(3,None,None))
                self.assertEqual(connection.execute('SELECT status FROM room_invitations').fetchone()[0],'revoked')
    def test_online_backup_includes_committed_wal_and_excludes_secrets(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);instance=root/'instance';instance.mkdir();(instance/'youtube.key').write_text('not-for-release')
            with closing(sqlite3.connect(instance/'afterglow.db')) as writer:
                writer.execute('PRAGMA journal_mode=WAL');writer.execute('CREATE TABLE saved(body TEXT)');writer.execute('INSERT INTO saved VALUES(?)',('Committed while open',));writer.commit()
                manifest=backup(instance,root/'saved');self.assertEqual(set(manifest['files']),{'afterglow.db'});restore(root/'saved',root/'restored')
                with closing(sqlite3.connect(root/'restored'/'afterglow.db')) as restored:self.assertEqual(restored.execute('SELECT body FROM saved').fetchone()[0],'Committed while open')
                self.assertFalse((root/'saved'/'youtube.key').exists())

    def test_retention_prunes_only_verified_owned_backups_with_no_extra_files(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);instance=root/'instance';instance.mkdir()
            with closing(sqlite3.connect(instance/'afterglow.db')) as connection:connection.execute('CREATE TABLE saved(body TEXT)');connection.commit()
            destination=root/'solace-backup-test';backup(instance,destination)
            manifest=json.loads((destination/'backup.json').read_text());manifest['created']=time.time()-10*86400;(destination/'backup.json').write_text(json.dumps(manifest))
            (destination/'keep.txt').write_text('Unknown file must protect this folder')
            self.assertEqual(prune(root,7),0);self.assertTrue(destination.exists())
            (destination/'keep.txt').unlink();self.assertEqual(prune(root,7),1);self.assertFalse(destination.exists())
