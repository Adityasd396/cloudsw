"""Room-scoped, server-authoritative Ludo. Two to four players, four pawns each."""
import json
import secrets
import time
from flask import jsonify,request,session
from game_options import agree,cheer

COLORS=('red','blue','yellow','green')
OFFSETS={color:i*13 for i,color in enumerate(COLORS)}
SAFE={0,8,13,21,26,34,39,47}
FINISH=56

def fresh(revision=0):
    return dict(players={},pawns={c:[-1]*4 for c in COLORS},turn='red',started=False,dice=None,winner=None,revision=revision,sixes=0,event=None)

def square(color,progress):
    return (OFFSETS[color]+progress)%52 if 0<=progress<51 else None

def legal(game,color,dice):
    result=[]
    for token,position in enumerate(game['pawns'][color]):
        if token>=game.get('pawn_count',4) or position==FINISH:continue
        if position==-1:
            if dice==6:result.append(token)
            continue
        target=position+dice
        if target>FINISH:continue
        blocked=False
        for step in range(position+1,min(target,50)+1):
            cell=square(color,step)
            if cell in SAFE:continue
            for other in game['players']:
                if other!=color and sum(square(other,p)==cell for p in game['pawns'][other])>=2:blocked=True
        if not blocked:result.append(token)
    return result

def next_turn(game):
    colors=[c for c in COLORS if c in game['players']]
    game['turn']=colors[(colors.index(game['turn'])+1)%len(colors)]
    game['sixes']=0

def register_ludo(app,db):
    @app.route('/api/rooms/<room_id>/ludo',methods=['GET','POST'])
    def room_ludo(room_id):
        connection=db();connection.execute('BEGIN IMMEDIATE')
        if not connection.execute('SELECT 1 FROM rooms WHERE id=?',(room_id,)).fetchone():return jsonify(error='Room not found.'),404
        members={r['id']:r['name'] for r in connection.execute('SELECT id,name FROM members WHERE room=?',(room_id,))}
        if session['uid'] not in members:return jsonify(error='Join the room first.'),403
        row=connection.execute('SELECT state FROM room_games WHERE room=?',(room_id,)).fetchone()
        state=json.loads(row['state']) if row else dict(board=['']*9,players={},turn='X',winner=None,revision=0);game=state.get('ludo') or fresh()
        if any(uid not in members for uid in game['players'].values()):game=fresh(game['revision']+1)
        game.setdefault('pawn_count',4)
        you=next((c for c,uid in game['players'].items() if uid==session['uid']),None)
        if request.method=='POST':
            data=request.get_json(silent=True)
            if not isinstance(data,dict):return jsonify(error='Invalid game action.'),400
            action=data.get('action')
            if action=='join':
                if not you:
                    if game['started']:return jsonify(error='A round is in progress. You can watch.'),409
                    you=next((c for c in COLORS if c not in game['players']),None)
                    if not you:return jsonify(error='Four players have joined.'),409
                    game['players'][you]=session['uid'];game['revision']+=1
            else:
                if not you:return jsonify(error='Join the game first.'),403
                if type(data.get('revision')) is not int or data['revision']!=game['revision']:return jsonify(error='Game updated. Your board will refresh.'),409
                if action=='configure':
                    values=data.get('values',{})
                    if game['started'] and not game['winner']:return jsonify(error='Finish this match first.'),409
                    if not isinstance(values,dict) or set(values)!={'pawn_count'} or type(values['pawn_count']) is not int or values['pawn_count'] not in (2,4):return jsonify(error='Invalid match length.'),400
                    if agree(game,you,values):
                        players=game['players'];revision=game['revision'];game=fresh(revision);game.update(players=players,pawn_count=values['pawn_count'])
                        if game['pawn_count']==2:
                            for c in COLORS:game['pawns'][c][2:]=[FINISH,FINISH]
                elif action=='start':
                    if game['started'] or len(game['players'])<2:return jsonify(error='At least two players must join.'),409
                    game['started']=True;game['turn']=next(c for c in COLORS if c in game['players'])
                elif action=='reset':
                    if not game['winner']:return jsonify(error='Finish this round first.'),409
                    if agree(game,you):
                        players=game['players'];revision=game['revision'];count=game['pawn_count'];game=fresh(revision);game.update(players=players,pawn_count=count)
                        if count==2:
                            for c in COLORS:game['pawns'][c][2:]=[FINISH,FINISH]
                elif action=='cheer':
                    try:cheer(game,you,data.get('emoji'))
                    except ValueError as error:return jsonify(error=str(error)),400
                elif action=='preview':
                    token=data.get('token')
                    if game['winner'] or not game['started'] or you!=game['turn'] or game['dice'] is None or type(token) is not int or token not in legal(game,you,game['dice']):return jsonify(error='Choose a legal pawn.'),409
                    game['selection']={'player':you,'token':token,'updated':time.time()}
                elif action in ('roll','move'):
                    game['selection']=None
                    if not game['started'] or game['winner'] or you!=game['turn']:return jsonify(error='Wait for your turn.'),409
                    if action=='roll':
                        if game['dice'] is not None:return jsonify(error='Choose a highlighted pawn.'),409
                        dice=secrets.randbelow(6)+1;game['dice']=dice;game['sixes']=game['sixes']+1 if dice==6 else 0
                        game['event']={'kind':'roll','player':you,'dice':dice,'created':time.time()}
                        if game['sixes']==3:
                            game['event']['kind']='three_sixes';game['dice']=None;next_turn(game)
                        elif not legal(game,you,dice):
                            game['event']['kind']='pass';game['dice']=None
                            if dice!=6:next_turn(game)
                    else:
                        token=data.get('token');dice=game['dice']
                        if dice is None or type(token) is not int or token not in legal(game,you,dice):return jsonify(error='Choose a highlighted pawn.'),400
                        old=game['pawns'][you][token];target=0 if old==-1 else old+dice;game['pawns'][you][token]=target;captured=[];cell=square(you,target)
                        if cell is not None and cell not in SAFE:
                            for other in game['players']:
                                if other==you:continue
                                for i,p in enumerate(game['pawns'][other]):
                                    if square(other,p)==cell:game['pawns'][other][i]=-1;captured.append([other,i])
                        game['event']={'kind':'move','player':you,'token':token,'from':old,'to':target,'captured':captured,'created':time.time()}
                        game['dice']=None
                        if all(p==FINISH for p in game['pawns'][you]):game['winner']=you
                        elif dice!=6 and not captured and target!=FINISH:next_turn(game)
                else:return jsonify(error='Unknown game action.'),400
                if action not in ('preview','cheer'):game['revision']+=1
            state['ludo']=game;connection.execute('INSERT INTO room_games VALUES(?,?) ON CONFLICT(room) DO UPDATE SET state=excluded.state',(room_id,json.dumps(state)))
        connection.commit()
        return jsonify(**{k:v for k,v in game.items() if k!='players'},players={c:members[uid] for c,uid in game['players'].items()},you=you,legal=legal(game,you,game['dice']) if you==game['turn'] and game['dice'] is not None else [],storage_generation=connection.execute("SELECT value FROM app_metadata WHERE key='generation'").fetchone()[0])
