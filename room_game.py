"""One transactional, two-player tic-tac-toe game per room."""
import json
import time
import secrets
from flask import jsonify, request, session
from ludo_game import register_ludo
from game_options import agree,cheer


def register_game(app, db):
    register_ludo(app,db)
    @app.route('/api/rooms/<room_id>/basketball', methods=['GET', 'POST'])
    def basketball(room_id):
        connection=db()
        connection.execute('BEGIN IMMEDIATE' if request.method=='POST' else 'BEGIN')
        if not connection.execute('SELECT 1 FROM rooms WHERE id=?',(room_id,)).fetchone():
            return jsonify(error='Room not found.'),404
        members={m['id']:m['name'] for m in connection.execute('SELECT id,name FROM members WHERE room=?',(room_id,))}
        if session['uid'] not in members:return jsonify(error='Join the room first.'),403
        row=connection.execute('SELECT state FROM room_games WHERE room=?',(room_id,)).fetchone()
        state=json.loads(row['state']) if row else dict(board=['']*9,players={},turn='X',winner=None,revision=0)
        game=state.get('basketball',dict(players={},scores={'X':0,'O':0},turn='X',winner=None,revision=0,shot=None))
        if any(uid not in members for uid in game['players'].values()):
            game=dict(players={},scores={'X':0,'O':0},turn='X',winner=None,revision=game['revision']+1,shot=None)
        game.setdefault('challenge',{'target':.5,'power':.62,'radius':.17})
        game.setdefault('attempts',{'X':0,'O':0});game.setdefault('streaks',{'X':0,'O':0})
        game.setdefault('mode','versus');game.setdefault('difficulty','relaxed')
        role=next((mark for mark,uid in game['players'].items() if uid==session['uid']),None)
        if request.method=='POST':
            data=request.get_json(silent=True)
            if not isinstance(data,dict):return jsonify(error='Invalid game action.'),400
            action=data.get('action')
            if action=='join':
                if not role:
                    role=next((mark for mark in ('X','O') if mark not in game['players']),None)
                    if not role:return jsonify(error='Two players are playing.'),409
                    game['players'][role]=session['uid'];game['revision']+=1
            elif action=='configure':
                values=data.get('values',{})
                if not role or len(game['players'])<2:return jsonify(error='Both players must join.'),409
                if sum(game['attempts'].values()) and not game['winner']:return jsonify(error='Finish the match first.'),409
                if not isinstance(values,dict) or set(values)!={'mode','difficulty'} or values['mode'] not in ('versus','together') or values['difficulty'] not in ('relaxed','challenging'):return jsonify(error='Invalid match options.'),400
                if agree(game,role,values):
                    game.update(values);game.update(scores={'X':0,'O':0},winner=None,shot=None,attempts={'X':0,'O':0},streaks={'X':0,'O':0},turn='X',live=None,challenge={'target':.5,'power':.62,'radius':.17 if values['difficulty']=='relaxed' else .10})
                game['revision']+=1
            elif action=='aim':
                if not role or role!=game['turn'] or len(game['players'])!=2 or game['winner']:return jsonify(error='Wait for your turn.'),409
                if type(data.get('revision')) is not int or data['revision']!=game['revision']:return jsonify(error='Shot changed.'),409
                a,power,phase=data.get('aim'),data.get('power'),data.get('phase')
                if type(a) not in (float,int) or not 0<=a<=1 or type(power) not in (float,int) or not 0<=power<=1 or phase not in ('aiming','charging','idle'):return jsonify(error='Invalid aiming state.'),400
                prior=game.get('live') or {}
                if phase=='idle' or time.time()-prior.get('updated',0)>=.15:game['live']={'player':role,'aim':a,'power':power,'phase':phase,'updated':time.time()}
            elif action=='cheer':
                if not role:return jsonify(error='Join the game first.'),403
                emoji=data.get('emoji')
                if emoji not in ('🫶','✨','👏'):return jsonify(error='Choose a cheer.'),400
                prior=game.get('cheer') or {}
                if time.time()-prior.get('created',0)<1:return jsonify(error='Give that cheer a moment.'),429
                game['cheer']={'id':secrets.token_hex(8),'player':role,'emoji':emoji,'created':time.time()}
            elif action in ('shoot','reset'):
                if not role:return jsonify(error='Join the game first.'),403
                if type(data.get('revision')) is not int or data['revision']!=game['revision']:
                    return jsonify(error='Game updated. Try again.'),409
                if action=='reset':
                    if not game['winner']:return jsonify(error='Finish this round first.'),409
                    if agree(game,role):game.update(scores={'X':0,'O':0},turn='X',winner=None,shot=None,live=None,attempts={'X':0,'O':0},streaks={'X':0,'O':0},challenge={'target':.5,'power':.62,'radius':.17 if game['difficulty']=='relaxed' else .10})
                else:
                    aim=data.get('aim')
                    if type(aim) not in (float,int) or not 0<=aim<=1:return jsonify(error='Invalid shot.'),400
                    if len(game['players'])!=2 or role!=game['turn'] or game['winner']:
                        return jsonify(error='Wait for your turn.'),409
                    power=data.get('power',.62)
                    if type(power) not in (int,float) or not 0<=power<=1:return jsonify(error='Invalid power.'),400
                    challenge=game['challenge'];goal=abs(aim-challenge['target'])<=challenge['radius'] and abs(power-challenge['power'])<=.12
                    game['attempts'][role]+=1;game['streaks'][role]=game['streaks'][role]+1 if goal else 0
                    game['scores'][role]+=int(goal)
                    game['shot']=dict(id=game['revision']+1,player=role,goal=goal,aim=aim,power=power,target=challenge['target'],rating='swish' if goal and abs(aim-challenge['target'])<.035 and abs(power-challenge['power'])<.04 else 'goal' if goal else 'miss')
                    game['live']=None
                    game['challenge']={'target':round(.3+secrets.randbelow(401)/1000,3),'power':round(.5+secrets.randbelow(281)/1000,3),'radius':(.17 if game['difficulty']=='relaxed' else .10)}
                    if game['mode']=='together' and sum(game['scores'].values())>=8:game['winner']='together'
                    elif game['scores'][role]>=5 and game['mode']=='versus':game['winner']=role
                    else:game['turn']='O' if role=='X' else 'X'
                game['revision']+=1
            else:return jsonify(error='Unknown game action.'),400
            state['basketball']=game
            connection.execute('INSERT INTO room_games VALUES(?,?) ON CONFLICT(room) DO UPDATE SET state=excluded.state',(room_id,json.dumps(state)))
        connection.commit()
        return jsonify(storage_generation=connection.execute("SELECT value FROM app_metadata WHERE key='generation'").fetchone()[0],**{k:v for k,v in game.items() if k!='players'},players={mark:members[uid] for mark,uid in game['players'].items()},you=role)

    @app.route('/api/rooms/<room_id>/game', methods=['GET', 'POST'])
    def room_game(room_id):
        connection=db()
        connection.execute('BEGIN IMMEDIATE' if request.method=='POST' else 'BEGIN')
        if not connection.execute('SELECT 1 FROM rooms WHERE id=?',(room_id,)).fetchone():
            return jsonify(error='Room not found.'),404
        members={m['id']:m['name'] for m in connection.execute('SELECT id,name FROM members WHERE room=?',(room_id,))}
        if session['uid'] not in members:
            return jsonify(error='Join the room first.'),403
        row=connection.execute('SELECT state FROM room_games WHERE room=?',(room_id,)).fetchone()
        game=json.loads(row['state']) if row else dict(board=['']*9,players={},turn='X',winner=None,revision=0)
        if any(uid not in members for uid in game['players'].values()):
            game={**{k:game[k] for k in ('basketball','ludo') if k in game},**dict(board=['']*9,players={},turn='X',winner=None,revision=game['revision']+1)}
        game.setdefault('best_of',1);game.setdefault('wins',{'X':0,'O':0});game.setdefault('round',1);game.setdefault('starter','X');game.setdefault('series_winner',None)
        role=next((mark for mark,uid in game['players'].items() if uid==session['uid']),None)
        if request.method=='POST':
            data=request.get_json(silent=True) or {}
            action=data.get('action')
            if action=='join':
                if not role:
                    role=next((mark for mark in ('X','O') if mark not in game['players']),None)
                    if not role:return jsonify(error='Two players are already playing. You can watch.'),409
                    game['players'][role]=session['uid']
                    game['revision']+=1
            elif action=='cheer':
                if not role:return jsonify(error='Join the game first.'),403
                try:cheer(game,role,data.get('emoji'))
                except ValueError as error:return jsonify(error=str(error)),400
            elif action=='configure':
                values=data.get('values',{})
                if not role or len(game['players'])<2:return jsonify(error='Both players must join.'),409
                if any(game['board']) and not game.get('series_winner') and not (game['best_of']==1 and game['winner']):return jsonify(error='Finish the match first.'),409
                if not isinstance(values,dict) or set(values)!={'best_of'} or type(values['best_of']) is not int or values['best_of'] not in (1,3,5):return jsonify(error='Invalid match length.'),400
                if agree(game,role,values):game.update(best_of=values['best_of'],board=['']*9,winner=None,series_winner=None,wins={'X':0,'O':0},round=1,starter='X',turn='X')
                game['revision']+=1
            elif action in ('move','reset'):
                if not role:return jsonify(error='Join the game to play.'),403
                if type(data.get('revision')) is not int or data.get('revision')!=game['revision']:
                    return jsonify(error='The game changed. Try again.'),409
                if action=='reset':
                    if not game['winner']:return jsonify(error='Finish this round before starting another.'),409
                    if agree(game,role):
                        starter='O' if game['starter']=='X' else 'X'
                        if game['series_winner']:game.update(wins={'X':0,'O':0},series_winner=None,round=0)
                        game.update(board=['']*9,turn=starter,starter=starter,winner=None,round=game['round']+1)
                else:
                    cell=data.get('cell')
                    if type(cell) is not int or not 0<=cell<9:return jsonify(error='Choose a square.'),400
                    if len(game['players'])!=2 or role!=game['turn'] or game['winner'] or game['board'][cell]:
                        return jsonify(error='Wait for your turn or choose an empty square.'),409
                    game['board'][cell]=role
                    lines=((0,1,2),(3,4,5),(6,7,8),(0,3,6),(1,4,7),(2,5,8),(0,4,8),(2,4,6))
                    if any(all(game['board'][i]==role for i in line) for line in lines):game['winner']=role
                    elif all(game['board']):game['winner']='draw'
                    else:game['turn']='O' if role=='X' else 'X'
                    if game['winner'] in ('X','O'):
                        game['wins'][role]+=1
                        if game['wins'][role]>=game['best_of']//2+1:game['series_winner']=role
                game['revision']+=1
            else:return jsonify(error='Unknown game action.'),400
            connection.execute('INSERT INTO room_games VALUES(?,?) ON CONFLICT(room) DO UPDATE SET state=excluded.state',(room_id,json.dumps(game)))
        connection.commit()
        return jsonify(storage_generation=connection.execute("SELECT value FROM app_metadata WHERE key='generation'").fetchone()[0],**{k:game[k] for k in ('best_of','wins','round','starter','series_winner','proposal','rematch_votes','cheer') if k in game},board=game['board'],players={mark:members[uid] for mark,uid in game['players'].items()},you=role,turn=game['turn'],winner=game['winner'],revision=game['revision'])
