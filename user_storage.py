"""Logical per-user storage accounting; quotas never interrupt room playback."""
import hashlib
import hmac

DEFAULT_BYTES=50*1024*1024

def register_user_storage(app,db):
    def usage(owner):
        account=db().execute('SELECT COALESCE(length(avatar),0)+length(CAST(email AS BLOB))+length(CAST(name AS BLOB))+256 FROM accounts WHERE id=?',(owner,)).fetchone()
        history=db().execute('''SELECT COALESCE(SUM(length(CAST(video AS BLOB))+length(CAST(title AS BLOB))+length(CAST(room AS BLOB))+length(CAST(playback AS BLOB))+64),0)
            FROM watch_history WHERE owner=?''',(owner,)).fetchone()[0]
        people=db().execute('''SELECT COALESCE(SUM(length(CAST(name AS BLOB))+32),0) FROM watch_people JOIN watch_history ON watch_history.id=watch_people.entry WHERE owner=?''',(owner,)).fetchone()[0]
        slices=db().execute('SELECT COUNT(*)*16 FROM watch_slices JOIN watch_history ON watch_history.id=watch_slices.entry WHERE owner=?',(owner,)).fetchone()[0]
        guest=db().execute('SELECT COALESCE(length(avatar),0)+128 FROM guest_data WHERE owner=?',(owner,)).fetchone()
        media=db().execute('SELECT COALESCE(SUM(bytes+128),0) FROM chat_media WHERE owner=?',(owner,)).fetchone()[0]
        messages=db().execute('SELECT COALESCE(SUM(length(CAST(body AS BLOB))+128),0) FROM dm_messages WHERE sender=?',(owner,)).fetchone()[0]
        world=db().execute('SELECT COALESCE(SUM(length(CAST(body AS BLOB))+128),0) FROM world_messages WHERE sender=?',(owner,)).fetchone()[0]
        return (account[0] if account else guest[0] if guest else 0)+history+people+slices+media+messages+world

    def limit(owner):
        row=db().execute('SELECT bytes FROM user_quotas WHERE owner=?',(owner,)).fetchone()
        default=db().execute("SELECT value FROM launch_settings WHERE key='user_storage_bytes'").fetchone()
        return row[0] if row else int(default[0]) if default else DEFAULT_BYTES

    def snapshot(owner):
        used=usage(owner);maximum=limit(owner)
        return {'reference':token(owner)[:8],'used_bytes':used,'limit_bytes':maximum,'remaining_bytes':max(0,maximum-used),'full':used>=maximum,'measurement':'Logical profiles, private and community message text, attachments and history; excludes shared room text, operations backups and database/index overhead.'}

    def token(owner):return hmac.new(str(app.secret_key).encode(),('storage:'+owner).encode(),hashlib.sha256).hexdigest()[:32]

    def owners(page=0):
        return db().execute('''SELECT identity,MAX(name) AS name,MAX(registered) AS registered FROM (
            SELECT id AS identity,name,1 AS registered FROM accounts UNION ALL
            SELECT owner AS identity,'Guest' AS name,0 AS registered FROM watch_history WHERE owner NOT IN (SELECT id FROM accounts) UNION ALL SELECT guest_data.owner AS identity,profiles.name AS name,0 AS registered FROM guest_data JOIN profiles ON profiles.id=guest_data.owner WHERE guest_data.owner NOT IN (SELECT id FROM accounts)) GROUP BY identity ORDER BY registered DESC,identity LIMIT 51 OFFSET ?''',(page*50,)).fetchall()

    app.extensions['solace_user_storage']={'usage':usage,'limit':limit,'snapshot':snapshot,'token':token,'owners':owners}
