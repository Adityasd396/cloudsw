import json
from contextlib import closing
from pathlib import Path
import sqlite3
import tempfile
import time
import unittest
from tools.storage import backup,restore,verify,prune

class StorageSafetyTests(unittest.TestCase):
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
