"""Owner-run retention cleanup. Outputs counts only; never messages or identifiers."""
import argparse,json,sqlite3,time
from contextlib import closing
from pathlib import Path

def cleanup(instance,now=None):
    root=Path(instance).resolve();now=time.time() if now is None else now;cutoff=now-30*86400;result={}
    for name in ['afterglow.db','solace-admin.db']:
        path=root/name
        if not path.exists():continue
        if path.is_symlink() or path.resolve().parent!=root:raise ValueError('Database must be inside the named instance directory')
        with closing(sqlite3.connect(path.as_uri()+'?mode=rw',uri=True,timeout=15)) as connection:
            tables={row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")};connection.execute('BEGIN IMMEDIATE')
            if name=='afterglow.db':
                for table,column in [('account_sessions','expires'),('account_tokens','expires'),('account_limits','until'),('native_handoffs','expires')]:
                    if table in tables:result[table]=connection.execute('DELETE FROM '+table+' WHERE '+column+'<?',(now,)).rowcount
                if 'safety_reports' in tables:
                    result['expired_evidence']=connection.execute('UPDATE safety_reports SET evidence=NULL WHERE evidence_until<? AND evidence IS NOT NULL',(now,)).rowcount
                    connection.execute('DELETE FROM safety_notes WHERE report IN (SELECT id FROM safety_reports WHERE created<?)',(now-180*86400,));connection.execute('DELETE FROM safety_reports WHERE created<?',(now-180*86400,));connection.execute('DELETE FROM safety_appeals WHERE created<?',(now-180*86400,))
                if 'world_messages' in tables:
                    connection.execute("DELETE FROM chat_media WHERE scope='world' AND message IN (SELECT id FROM world_messages WHERE created<?)",(cutoff,));result['world_messages']=connection.execute('DELETE FROM world_messages WHERE created<?',(cutoff,)).rowcount;connection.execute('DELETE FROM world_receipts WHERE created<?',(cutoff,));connection.execute('DELETE FROM world_presence WHERE expires<?',(now,));connection.execute('UPDATE world_state SET revision=revision+1 WHERE id=1')
                if 'discovery_leases' in tables:connection.execute('DELETE FROM discovery_leases WHERE expires<?',(now,))
                if 'chat_media' in tables:result['unused_uploads']=connection.execute('DELETE FROM chat_media WHERE message IS NULL AND uploaded<?',(now-86400,)).rowcount
                if {'watch_history','accounts','watch_people','watch_slices'}<=tables:
                    where='SELECT watch_history.id FROM watch_history LEFT JOIN accounts ON accounts.id=watch_history.owner WHERE accounts.id IS NULL AND watch_history.last<?'
                    for table in ['watch_people','watch_slices']:connection.execute('DELETE FROM '+table+' WHERE entry IN ('+where+')',(cutoff,))
                    result['guest_history']=connection.execute('DELETE FROM watch_history WHERE id IN ('+where+')',(cutoff,)).rowcount
            else:
                for table,column in [('visitors','last'),('visitor_ips','last'),('events','created'),('chat_archive','created'),('requests','minute'),('client_diagnostics','received'),('diagnostic_events','created'),('staff_security','created')]:
                    if table in tables:result[table]=connection.execute('DELETE FROM '+table+' WHERE '+column+'<?',(cutoff/60 if column=='minute' else cutoff,)).rowcount
            connection.commit()
    return result

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--instance',required=True);args=parser.parse_args();print(json.dumps({'deleted':cleanup(args.instance)}))
