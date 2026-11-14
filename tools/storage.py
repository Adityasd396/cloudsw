"""Verified SQLite backups and safe restore into a NEW instance directory only."""
from contextlib import closing
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import secrets
import sqlite3
import time

FILES={'afterglow.db','solace-admin.db'}

def check_database(path):
    with closing(sqlite3.connect(path.resolve().as_uri()+'?mode=ro',uri=True)) as connection:
        if connection.execute('PRAGMA quick_check').fetchone()[0]!='ok':raise ValueError('Database integrity check failed')

def backup(instance,output):
    instance=Path(instance).resolve();output=Path(output).resolve()
    if output.exists():raise ValueError('Choose a new backup directory')
    if not (instance/'afterglow.db').is_file():raise ValueError('Room database not found')
    output.mkdir(parents=True,mode=0o700)
    manifest={'format':'solace-backup-v1','created':time.time(),'files':{}}
    for name in sorted(FILES):
        source=instance/name
        if not source.exists():continue
        destination=output/name
        with closing(sqlite3.connect(source.as_uri()+'?mode=ro',uri=True)) as reader,closing(sqlite3.connect(destination)) as writer:reader.backup(writer,pages=128,sleep=.02)
        check_database(destination);destination.chmod(0o600)
        manifest['files'][name]=hashlib.sha256(destination.read_bytes()).hexdigest()
    (output/'backup.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
    (output/'backup.json').chmod(0o600)
    return manifest

def verify(source):
    source=Path(source).resolve();manifest=json.loads((source/'backup.json').read_text(encoding='utf-8'))
    if manifest.get('format')!='solace-backup-v1' or not manifest.get('files') or not set(manifest['files'])<=FILES:raise ValueError('Invalid backup manifest')
    for name,digest in manifest['files'].items():
        path=(source/name).resolve()
        if path.parent!=source or hashlib.sha256(path.read_bytes()).hexdigest()!=digest:raise ValueError('Backup checksum mismatch')
        check_database(path)
    return manifest

def restore(source,target):
    source=Path(source).resolve();target=Path(target).resolve();manifest=verify(source)
    if target.exists():raise ValueError('Restore target must not already exist; existing data is never overwritten')
    target.mkdir(parents=True,mode=0o700)
    for name in manifest['files']:
        shutil.copyfile(source/name,target/name);(target/name).chmod(0o600);check_database(target/name)
        if name=='afterglow.db':
            with closing(sqlite3.connect(target/name)) as connection:
                connection.execute('CREATE TABLE IF NOT EXISTS app_metadata(key TEXT PRIMARY KEY,value TEXT NOT NULL)')
                connection.execute("INSERT INTO app_metadata VALUES('generation',?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",(secrets.token_hex(16),));connection.commit()
        if name=='solace-admin.db':
            with closing(sqlite3.connect(target/name)) as connection:
                if connection.execute("SELECT 1 FROM sqlite_master WHERE name='admin_sessions'").fetchone():connection.execute('DELETE FROM admin_sessions');connection.commit()
    return manifest

def prune(folder,days):
    folder=Path(folder).resolve();removed=0
    if days<1:raise ValueError('Retention must be at least one day')
    for child in folder.glob('solace-backup-*'):
        if child.is_symlink() or not child.is_dir() or child.resolve().parent!=folder:continue
        try:manifest=verify(child)
        except (OSError,ValueError,sqlite3.Error):continue
        if manifest['created']>=time.time()-days*86400:continue
        if set(p.name for p in child.iterdir())!=set(manifest['files'])|{'backup.json'}:continue
        for name in list(manifest['files'])+['backup.json']:(child/name).unlink()
        child.rmdir();removed+=1
    return removed

if __name__=='__main__':
    parser=argparse.ArgumentParser();sub=parser.add_subparsers(dest='action',required=True)
    save=sub.add_parser('backup');save.add_argument('--instance',required=True);save.add_argument('--output',required=True)
    load=sub.add_parser('restore');load.add_argument('--backup',required=True);load.add_argument('--target',required=True)
    validate=sub.add_parser('verify');validate.add_argument('--backup',required=True)
    trim=sub.add_parser('prune');trim.add_argument('--folder',required=True);trim.add_argument('--days',type=int,default=7)
    args=parser.parse_args()
    if args.action=='backup':result=backup(args.instance,args.output)
    elif args.action=='restore':result=restore(args.backup,args.target)
    elif args.action=='verify':result=verify(args.backup)
    else:result={'removed':prune(args.folder,args.days)}
    print(json.dumps({'ok':True,'files':sorted(result.get('files',{})),'removed':result.get('removed',0)}))
