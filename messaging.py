"""Private friend conversations and validated room/DM image attachments.

Media bytes stay in SQLite so online backups remain complete and atomic.
No message bodies, image names or participant identifiers enter operations logs.
"""
import hashlib,io,re,secrets,time,warnings,threading
from flask import abort,g,jsonify,redirect,render_template,request,send_file,session
from PIL import Image,ImageOps,UnidentifiedImageError,__version__ as pillow_version
from werkzeug.exceptions import HTTPException

MAX_UPLOAD=8*1024*1024

def register_messaging(app,db,limited,csrf_valid):
    ready=set();image_gate=threading.BoundedSemaphore(1)
    @app.errorhandler(HTTPException)
    def communication_error(error):
        if request.path.startswith(('/api/me/conversations','/api/me/media','/api/me/room-media','/api/me/world','/api/me/preferences','/api/me/chat','/api/me/play','/api/me/notifications','/api/me/moments','/api/rooms/g_')):return jsonify(error=error.description),error.code
        return error
    def initialize():
        if app.instance_path in ready:return
        db().executescript('''BEGIN IMMEDIATE;
        CREATE TABLE IF NOT EXISTS dm_conversations(id TEXT PRIMARY KEY,a TEXT NOT NULL,b TEXT NOT NULL,created REAL NOT NULL,UNIQUE(a,b));
        CREATE TABLE IF NOT EXISTS dm_inbox(conversation TEXT NOT NULL REFERENCES dm_conversations(id) ON DELETE CASCADE,owner TEXT NOT NULL,hidden_until INTEGER NOT NULL DEFAULT 0,read_id INTEGER NOT NULL DEFAULT 0,PRIMARY KEY(conversation,owner));
        CREATE INDEX IF NOT EXISTS dm_owner ON dm_inbox(owner,conversation);
        CREATE TABLE IF NOT EXISTS dm_messages(id INTEGER PRIMARY KEY AUTOINCREMENT,conversation TEXT NOT NULL REFERENCES dm_conversations(id) ON DELETE CASCADE,sender TEXT NOT NULL,body TEXT NOT NULL,created REAL NOT NULL,request_id TEXT NOT NULL,digest TEXT NOT NULL,deleted INTEGER NOT NULL DEFAULT 0,media_id TEXT,UNIQUE(conversation,sender,request_id));
        CREATE INDEX IF NOT EXISTS dm_page ON dm_messages(conversation,id);
        CREATE INDEX IF NOT EXISTS dm_sender ON dm_messages(sender);
        CREATE TABLE IF NOT EXISTS dm_typing(conversation TEXT NOT NULL REFERENCES dm_conversations(id) ON DELETE CASCADE,owner TEXT NOT NULL,updated REAL NOT NULL,PRIMARY KEY(conversation,owner));
        CREATE TABLE IF NOT EXISTS chat_media(id TEXT PRIMARY KEY,owner TEXT NOT NULL,scope TEXT NOT NULL,scope_id TEXT NOT NULL,uploaded REAL NOT NULL,upload_key TEXT NOT NULL,digest TEXT NOT NULL,data BLOB,poster BLOB,mime TEXT NOT NULL,width INTEGER NOT NULL,height INTEGER NOT NULL,animated INTEGER NOT NULL,bytes INTEGER NOT NULL,message INTEGER,deleted INTEGER NOT NULL DEFAULT 0,UNIQUE(owner,scope,scope_id,upload_key));
        CREATE INDEX IF NOT EXISTS media_owner ON chat_media(owner);
        CREATE INDEX IF NOT EXISTS media_scope ON chat_media(scope,scope_id,message);
        CREATE TABLE IF NOT EXISTS media_sends(owner TEXT NOT NULL,room TEXT NOT NULL,request_id TEXT NOT NULL,digest TEXT NOT NULL,message INTEGER NOT NULL,PRIMARY KEY(owner,room,request_id));
        COMMIT;''')
        if 'share_read' not in {r['name'] for r in db().execute('PRAGMA table_info(social_profiles)')}:
            db().execute('BEGIN IMMEDIATE')
            if 'share_read' not in {r['name'] for r in db().execute('PRAGMA table_info(social_profiles)')}:db().execute('ALTER TABLE social_profiles ADD COLUMN share_read INTEGER NOT NULL DEFAULT 0')
            db().commit()
        db().execute('INSERT OR IGNORE INTO launch_migrations VALUES(5,?)',(time.time(),));db().commit();ready.add(app.instance_path)

    def social():return app.extensions['solace_social']
    def owner():return social()['named']()['id']
    def fail(text,status=400):return jsonify(error=text),status
    def begin():
        if not db().in_transaction:db().execute('BEGIN IMMEDIATE')
    def key(value):
        if not isinstance(value,str) or not re.fullmatch(r'[A-Za-z0-9_-]{12,80}',value):abort(400,description='Use a valid request identifier.')
        return value
    def body():
        data=request.get_json(silent=True) or {};text=data.get('body','')
        if not isinstance(text,str) or len(text)>2000 or any(ord(c)<32 and c not in '\n\t' for c in text):abort(400,description='Use a message up to 2,000 characters.')
        media=data.get('media_id')
        if media is not None and (not isinstance(media,str) or len(media)>80):abort(400)
        return data,text.strip(),media,key(data.get('request_id'))
    def conversation(cid,write=False,allow_blocked=False):
        uid=owner();row=db().execute('SELECT c.*,i.hidden_until,i.read_id FROM dm_conversations c JOIN dm_inbox i ON i.conversation=c.id AND i.owner=? WHERE c.id=?',(uid,cid)).fetchone()
        if not row:abort(404,description='Conversation unavailable.')
        other=row['b'] if row['a']==uid else row['a']
        if not allow_blocked and social()['blocked'](uid,other):abort(403,description='This conversation is unavailable because of a block.')
        if write and app.extensions.get('solace_safety') and app.extensions['solace_safety']['restricted'](other):abort(403,description='This profile is unavailable for messaging.')
        if write and (not social()['friends'](uid,other) or not social()['person'](other)):abort(403,description='You must be accepted friends to send messages.')
        return row,other
    def room_member(room):
        row=db().execute('SELECT r.host,m.name FROM rooms r JOIN members m ON m.room=r.id AND m.id=? WHERE r.id=?',(session['uid'],room)).fetchone()
        if not row:abort(403,description='Join this room to access its attachments.')
        return row
    def permission(scope,sid,write=False):
        if scope=='room':return room_member(sid)
        if scope=='dm':return conversation(sid,write)
        if scope=='world' and sid=='community':return app.extensions['solace_world']['access'](write)
        abort(400)
    def media_info(row):
        return dict(id=row['id'],url='/api/me/media/'+row['id'],poster='/api/me/media/'+row['id']+'?poster=1',width=row['width'],height=row['height'],animated=bool(row['animated']),deleted=bool(row['deleted']),you=row['owner']==session['uid'])
    def picture(raw):
        if tuple(int(p) for p in pillow_version.split('.')[:2])<(13,0):abort(503,description='Update the server image library before enabling uploads.')
        try:
            with warnings.catch_warnings():
                warnings.simplefilter('error',Image.DecompressionBombWarning)
                with Image.open(io.BytesIO(raw),formats=['JPEG','PNG','WEBP','GIF']) as image:
                    frames=getattr(image,'n_frames',1)
                    if image.width*image.height>16_000_000 or frames>180 or image.width*image.height*frames>40_000_000:raise ValueError()
                    if frames>1 and image.format!='GIF':raise ValueError()
                    animated=image.format=='GIF' and frames>1;out=io.BytesIO();poster=io.BytesIO()
                    if animated:
                        copies=[];durations=[]
                        for index in range(frames):
                            image.seek(index);frame=image.convert('RGBA');frame.thumbnail((800,800));frame.info.clear();copies.append(frame);durations.append(max(20,min(10000,int(image.info.get('duration',100)))))
                        if sum(durations)>120000:raise ValueError()
                        copies[0].convert('RGB').save(poster,'JPEG',quality=85)
                        copies[0].save(out,'GIF',save_all=True,append_images=copies[1:],duration=durations,loop=0,disposal=2,optimize=False)
                        width,height=copies[0].size;mime='image/gif'
                    else:
                        image.load();frame=ImageOps.exif_transpose(image).convert('RGB');frame.thumbnail((1600,1600));frame.info.clear();frame.save(out,'JPEG',quality=88,optimize=True);width,height=frame.size;mime='image/jpeg'
                    encoded=out.getvalue();still=poster.getvalue()
                    if len(encoded)+len(still)>MAX_UPLOAD:raise ValueError()
                    return encoded,still,mime,width,height,animated
        except (UnidentifiedImageError,OSError,ValueError,SyntaxError,EOFError,Image.DecompressionBombWarning,Image.DecompressionBombError):abort(400,description='Choose a valid JPEG, PNG, WebP or GIF. Maximum 16 megapixels; GIFs: 180 frames, 40 million decoded pixels and 2 minutes.')

    @app.before_request
    def media_body_limit():
        if request.path=='/api/me/media' and request.method=='POST':request.max_content_length=MAX_UPLOAD+16384

    @app.get('/settings')
    @app.get('/games')
    def space_page():
        if not social()['person'](session['uid']):return redirect('/welcome',303)
        room=db().execute('SELECT room FROM members WHERE id=? ORDER BY seen DESC LIMIT 1',(session['uid'],)).fetchone()
        return render_template('space-settings.html' if request.path=='/settings' else 'space-games.html',game_room=room['room'] if room else None)

    @app.get('/room-media')
    def room_media_page():
        room=request.args.get('room','');room_member(room);return render_template('room-media.html',room=room)

    @app.get('/media-view')
    def media_view_page():
        row=db().execute('SELECT * FROM chat_media WHERE id=?',(request.args.get('media'),)).fetchone()
        if not row or row['deleted'] or (row['message'] is None and row['owner']!=session['uid']):abort(404)
        permitted=permission(row['scope'],row['scope_id']);info=media_info(row);info['can_remove']=row['owner']==session['uid'] or (row['scope']=='room' and permitted['host']==session['uid']);return render_template('media-view.html',media=info)

    @app.get('/messages')
    def messages_page():
        if not social()['person'](session['uid']):return redirect('/welcome',303)
        return render_template('messages.html')

    @app.route('/api/me/conversations',methods=['GET','POST'])
    def conversations():
        uid=owner()
        if request.method=='POST':
            if limited('dm-open:'+uid,30,60):return fail('Please wait before opening another chat.',429)
            code=(request.get_json(silent=True) or {}).get('code');other=social()['resolve'](code)
            if not other or other==uid or social()['blocked'](uid,other) or not social()['friends'](uid,other):return fail('Start a chat with an accepted friend.',403)
            begin();a,b=sorted((uid,other));db().execute('INSERT OR IGNORE INTO dm_conversations VALUES(?,?,?,?)',(secrets.token_urlsafe(18),a,b,time.time()));row=db().execute('SELECT id FROM dm_conversations WHERE a=? AND b=?',(a,b)).fetchone()
            for person in (a,b):db().execute('INSERT OR IGNORE INTO dm_inbox(conversation,owner) VALUES(?,?)',(row['id'],person))
            # Explicitly reopening a hidden conversation restores its history for this owner only.
            db().execute('UPDATE dm_inbox SET hidden_until=0 WHERE conversation=? AND owner=?',(row['id'],uid));db().commit();return jsonify(id=row['id'])
        try:offset=int(request.args.get('offset','0'));assert 0<=offset<=100000
        except (ValueError,AssertionError):return fail('Invalid inbox page.')
        rows=db().execute('''SELECT c.*,i.hidden_until,i.read_id,COALESCE(MAX(m.id),0) AS last_id FROM dm_inbox i JOIN dm_conversations c ON c.id=i.conversation LEFT JOIN dm_messages m ON m.conversation=c.id WHERE i.owner=? GROUP BY c.id HAVING i.hidden_until=0 OR (i.hidden_until=-1 AND last_id>0) OR (i.hidden_until>0 AND last_id>i.hidden_until) ORDER BY last_id DESC,c.created DESC LIMIT 31 OFFSET ?''',(uid,offset)).fetchall();items=[]
        for r in rows[:30]:
            other=r['b'] if r['a']==uid else r['a']
            if social()['blocked'](uid,other):continue
            p=social()['card'](other,uid,social()['friends'](uid,other)) or {'name':'Former participant','avatar':'/static/default-avatar.svg','code':None,'online':None}
            last=db().execute('SELECT * FROM dm_messages WHERE conversation=? ORDER BY id DESC LIMIT 1',(r['id'],)).fetchone()
            unread=db().execute('SELECT COUNT(*) FROM dm_messages WHERE conversation=? AND id>? AND sender<>? AND deleted=0',(r['id'],max(r['read_id'],r['hidden_until']),uid)).fetchone()[0]
            items.append(dict(id=r['id'],person=p,preview=('Say hello' if not last else 'Message removed' if last['deleted'] else last['body'] or 'Picture'),created=last['created'] if last else r['created'],unread=unread))
        db().commit();return jsonify(conversations=items,has_more=len(rows)>30,next_offset=offset+30)

    def serialize(row):
        p=social()['person'](row['sender']);result=dict(id=row['id'],body=row['body'] if not row['deleted'] else '',created=row['created'],you=row['sender']==session['uid'],name=p['name'] if p else 'Former participant',deleted=bool(row['deleted']),request_id=row['request_id'] if row['sender']==session['uid'] else None,media=None)
        if row['media_id']:
            media=db().execute('SELECT id,owner,width,height,animated,deleted FROM chat_media WHERE id=?',(row['media_id'],)).fetchone()
            if media:result['media']=media_info(media)
        return result

    @app.route('/api/me/conversations/<cid>',methods=['GET','POST','DELETE'])
    def conversation_messages(cid):
        uid=owner()
        if request.method=='DELETE':
            begin();conversation(cid,allow_blocked=True);latest=db().execute('SELECT COALESCE(MAX(id),0) FROM dm_messages WHERE conversation=?',(cid,)).fetchone()[0]
            db().execute('UPDATE dm_inbox SET hidden_until=?,read_id=? WHERE conversation=? AND owner=?',(latest if latest else -1,latest,cid,uid));db().commit();return jsonify(ok=True)
        if request.method=='POST':
            if limited('dm-send:'+uid,60,60):return fail('Please slow down for a moment.',429)
            data,text,media_id,rid=body()
            if not text and not media_id:return fail('Write a message or choose a picture.')
            digest=hashlib.sha256((text+'\0'+str(media_id)).encode()).hexdigest();begin();conversation(cid,True)
            old=db().execute('SELECT * FROM dm_messages WHERE conversation=? AND sender=? AND request_id=?',(cid,uid,rid)).fetchone()
            if old:
                if old['digest']!=digest:return fail('This send identifier was already used for different content.',409)
                db().commit();return jsonify(message=serialize(old))
            if media_id:staged_media(media_id,'dm',cid,uid)
            if app.extensions['solace_user_storage']['usage'](uid)+len(text.encode())+128>app.extensions['solace_user_storage']['limit'](uid):return fail('Your storage limit is reached. Remove old media or messages.',413)
            mid=db().execute('INSERT INTO dm_messages(conversation,sender,body,created,request_id,digest,media_id) VALUES(?,?,?,?,?,?,?)',(cid,uid,text,time.time(),rid,digest,media_id)).lastrowid
            if media_id:db().execute('UPDATE chat_media SET message=? WHERE id=?',(mid,media_id))
            db().execute('UPDATE dm_inbox SET hidden_until=0,read_id=MAX(read_id,?) WHERE conversation=? AND owner=?',(mid,cid,uid));db().commit()
            return jsonify(message=serialize(db().execute('SELECT * FROM dm_messages WHERE id=?',(mid,)).fetchone())),201
        row,other=conversation(cid)
        try:
            before=int(request.args.get('before','0'));after=int(request.args.get('after','0'));assert before>=0 and after>=0 and not (before and after)
        except (ValueError,AssertionError):return fail('Invalid message page.')
        sql='SELECT * FROM dm_messages WHERE conversation=?';params=[cid]
        if before:sql+=' AND id<?';params.append(before)
        if after:sql+=' AND id>?';params.append(after)
        records=db().execute(sql+' ORDER BY id '+('ASC' if after else 'DESC')+' LIMIT 51',params).fetchall();has_more=len(records)>50;records=records[:50];records=records if after else list(reversed(records))
        p=social()['card'](other,uid,social()['friends'](uid,other)) or {'name':'Former participant','avatar':'/static/default-avatar.svg','online':None,'code':None};mine=social()['social_profile'](uid);theirs=social()['social_profile'](other) if social()['person'](other) else None
        read=None
        if social()['friends'](uid,other) and mine.get('share_read') and theirs and theirs.get('share_read'):
            receipt=db().execute('SELECT read_id FROM dm_inbox WHERE conversation=? AND owner=?',(cid,other)).fetchone();read=receipt['read_id'] if receipt else 0
        typing=bool(db().execute('SELECT 1 FROM dm_typing WHERE conversation=? AND owner=? AND updated>?',(cid,other,time.time()-5)).fetchone()) if social()['friends'](uid,other) else False
        changes=[{'id':r['id'],'deleted':True} for r in db().execute('SELECT id FROM dm_messages WHERE conversation=? AND deleted=1 ORDER BY id DESC LIMIT 100',(cid,))]
        db().commit();return jsonify(messages=[serialize(r) for r in records],has_more=has_more,person=p,typing=typing,read_id=read,can_send=social()['friends'](uid,other) and bool(social()['person'](other)),removed=changes,media_removed=[r['message'] for r in db().execute("SELECT message FROM chat_media WHERE scope='dm' AND scope_id=? AND deleted=1 AND message IS NOT NULL ORDER BY message DESC LIMIT 100",(cid,))])

    @app.post('/api/me/conversations/<cid>/state')
    def conversation_state(cid):
        uid=owner()
        if limited('dm-state:'+uid,150,60):return fail('Please wait a moment.',429)
        data=request.get_json(silent=True) or {};begin();conversation(cid)
        if 'read_id' in data:
            rid=data['read_id']
            if type(rid) is not int or rid<0:return fail('Invalid read marker.')
            maximum=db().execute('SELECT COALESCE(MAX(id),0) FROM dm_messages WHERE conversation=?',(cid,)).fetchone()[0]
            db().execute('UPDATE dm_inbox SET read_id=MAX(read_id,?) WHERE conversation=? AND owner=?',(min(rid,maximum),cid,uid))
        if data.get('typing') is True:
            conversation(cid,True);db().execute('INSERT INTO dm_typing VALUES(?,?,?) ON CONFLICT(conversation,owner) DO UPDATE SET updated=excluded.updated',(cid,uid,time.time()))
        elif 'typing' in data:db().execute('DELETE FROM dm_typing WHERE conversation=? AND owner=?',(cid,uid))
        db().commit();return jsonify(ok=True)

    @app.delete('/api/me/conversations/<cid>/messages/<int:mid>')
    def remove_message(cid,mid):
        uid=owner();begin()
        row=db().execute('SELECT * FROM dm_messages WHERE conversation=? AND id=? AND sender=?',(cid,mid,uid)).fetchone()
        if not row:return fail('Only your own messages can be removed.',403)
        db().execute("UPDATE dm_messages SET body='',deleted=1 WHERE id=?",(mid,))
        if row['media_id']:erase_media(row['media_id'])
        db().commit();return jsonify(ok=True)

    def staged_media(mid,scope,sid,uid):
        row=db().execute('SELECT id FROM chat_media WHERE id=? AND owner=? AND scope=? AND scope_id=? AND message IS NULL AND deleted=0 AND uploaded>?',(mid,uid,scope,sid,time.time()-86400)).fetchone()
        if not row:abort(409,description='This attachment expired, was removed or has already been sent.')

    @app.post('/api/me/media')
    def upload():
        uid=owner()
        if limited('media-upload:'+uid,15,60):return fail('Please wait before uploading again.',429)
        scope=request.form.get('scope');sid=request.form.get('scope_id','');rid=key(request.form.get('upload_key'));permission(scope,sid,True)
        upload=request.files.get('picture')
        if not upload:return fail('Choose a picture or GIF up to 8 MiB.')
        raw=upload.read(MAX_UPLOAD+1)
        if not raw or len(raw)>MAX_UPLOAD:return fail('Use a picture or GIF no larger than 8 MiB.',413)
        digest=hashlib.sha256(raw).hexdigest();old=db().execute('SELECT * FROM chat_media WHERE owner=? AND scope=? AND scope_id=? AND upload_key=?',(uid,scope,sid,rid)).fetchone()
        if old:
            if old['digest']!=digest or old['deleted']:return fail('This upload identifier has already been used.',409)
            return jsonify(media=media_info(old))
        if not image_gate.acquire(blocking=False):return fail('Another picture is being processed. Please retry in a moment.',503)
        try:data,poster,mime,width,height,animated=picture(raw)
        finally:image_gate.release()
        begin();permission(scope,sid,True)
        quota=app.extensions['solace_user_storage'];size=len(data)+len(poster)
        if quota['usage'](uid)+size+128>quota['limit'](uid):return fail('Your storage limit is reached. Remove old attachments or history.',413)
        # Recheck under the write lock to make simultaneous retries one upload.
        old=db().execute('SELECT * FROM chat_media WHERE owner=? AND scope=? AND scope_id=? AND upload_key=?',(uid,scope,sid,rid)).fetchone()
        if old:
            if old['digest']!=digest or old['deleted']:return fail('This upload identifier has already been used.',409)
            db().commit();return jsonify(media=media_info(old))
        mid=secrets.token_urlsafe(24);db().execute('INSERT INTO chat_media(id,owner,scope,scope_id,uploaded,upload_key,digest,data,poster,mime,width,height,animated,bytes) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)',(mid,uid,scope,sid,time.time(),rid,digest,data,poster,mime,width,height,int(animated),size));db().commit()
        return jsonify(media=media_info(db().execute('SELECT * FROM chat_media WHERE id=?',(mid,)).fetchone())),201

    @app.route('/api/me/media/<mid>',methods=['GET','DELETE'])
    def media(mid):
        uid=owner()
        if request.method=='DELETE':begin()
        row=db().execute('SELECT * FROM chat_media WHERE id=?',(mid,)).fetchone()
        if not row:abort(404)
        if row['scope']=='world' and social()['blocked'](uid,row['owner']):abort(404)
        permitted=permission(row['scope'],row['scope_id']) if request.method=='GET' or row['owner']!=uid else None
        if request.method=='DELETE':
            host=permitted['host'] if row['scope']=='room' and permitted else None
            if row['owner']!=uid and host!=uid:return fail('Only the sender or room host can remove this attachment.',403)
            erase_media(mid);db().commit();return jsonify(ok=True)
        if row['deleted']:abort(410)
        if row['message'] is None and row['owner']!=uid:abort(404)
        still=bool(request.args.get('poster')) and row['animated'];response=send_file(io.BytesIO(row['poster'] if still else row['data']),mimetype='image/jpeg' if still else row['mime'],max_age=0)
        response.headers['Content-Disposition']='inline; filename="solace-picture.'+('jpg' if still or not row['animated'] else 'gif')+'"';response.headers['Content-Security-Policy']="default-src 'none'; sandbox";return response

    def erase_media(mid):
        row=db().execute('SELECT scope FROM chat_media WHERE id=?',(mid,)).fetchone()
        db().execute('UPDATE chat_media SET data=NULL,poster=NULL,bytes=0,deleted=1,uploaded=? WHERE id=?',(time.time(),mid))
        if row and row['scope']=='world':app.extensions['solace_world']['bump']()

    @app.post('/api/me/room-media/<room>/send')
    def room_send(room):
        uid=owner()
        if limited('room-media-send:'+uid,30,60):return fail('Please slow down for a moment.',429)
        data,text,mid,rid=body()
        if not mid or len(text)>500:return fail('Choose a picture and a caption up to 500 characters.')
        digest=hashlib.sha256((text+'\0'+mid).encode()).hexdigest();begin();member=room_member(room)
        old=db().execute('SELECT * FROM media_sends WHERE owner=? AND room=? AND request_id=?',(uid,room,rid)).fetchone()
        if old:
            if old['digest']!=digest:return fail('This send identifier was already used.',409)
            db().commit();return jsonify(ok=True,message=old['message'])
        staged_media(mid,'room',room,uid)
        message=db().execute('INSERT INTO messages(room,name,body,created,sender) VALUES(?,?,?,?,?)',(room,member['name'],text or 'Picture',time.time(),uid)).lastrowid
        db().execute('UPDATE chat_media SET message=?,uploaded=? WHERE id=?',(message,time.time(),mid));db().execute('INSERT INTO media_sends VALUES(?,?,?,?,?)',(uid,room,rid,digest,message));db().commit();return jsonify(ok=True,message=message),201

    def room_items(room):
        latest=db().execute("SELECT COALESCE(MAX(uploaded),0) FROM chat_media WHERE scope='room' AND scope_id=? AND message IS NOT NULL",(room,)).fetchone()[0];revision=format(latest,'.6f')
        if request.args.get('media_after')==revision:return revision,None
        return revision,[{**media_info(r),'message':r['message']} for r in db().execute('SELECT id,owner,width,height,animated,deleted,message FROM chat_media WHERE scope=\'room\' AND scope_id=? AND message IS NOT NULL ORDER BY message DESC LIMIT 100',(room,))]
    def erase_room(room):
        if not db().execute("SELECT 1 FROM sqlite_master WHERE name='chat_media'").fetchone():return
        db().execute("DELETE FROM chat_media WHERE scope='room' AND scope_id=?",(room,));db().execute('DELETE FROM media_sends WHERE room=?',(room,))
    def erase_owner(uid):
        app.extensions['solace_companions']['erase_owner'](uid)
        db().execute("UPDATE world_messages SET body='',deleted=1 WHERE sender=?",(uid,));app.extensions['solace_world']['bump']()
        db().execute('DELETE FROM user_preferences WHERE owner=?',(uid,));db().execute('DELETE FROM world_presence WHERE owner=?',(uid,))
        db().execute('UPDATE chat_media SET data=NULL,poster=NULL,bytes=0,deleted=1 WHERE owner=?',(uid,));db().execute("UPDATE dm_messages SET body='',deleted=1 WHERE sender=?",(uid,));db().execute('DELETE FROM dm_typing WHERE owner=?',(uid,))
        db().execute('DELETE FROM dm_inbox WHERE owner=?',(uid,))
    app.extensions['solace_messaging']={'initialize':initialize,'conversation':conversation,'room_items':room_items,'erase_room':erase_room,'erase_owner':erase_owner,'body':body,'staged_media':staged_media,'media_info':media_info,'erase_media':erase_media}
