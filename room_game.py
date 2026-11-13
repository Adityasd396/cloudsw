"""One transactional, two-player tic-tac-toe game per room."""
import json
from flask import jsonify, request, session


def register_game(app, db):
    @app.route('/api/rooms/<room_id>/basketball', methods=['GET', 'POST'])
    def basketball(room_id):
        connection=db()
        connection.execute('BEGIN IMMEDIATE')
        if not connection.execute('SELECT 1 FROM rooms WHERE id=?',(room_id,)).fetchone():
            return jsonify(error='Room not found.'),404
        members={m['id']:m['name'] for m in connection.execute('SELECT id,name FROM members WHERE room=?',(room_id,))}
        if session['uid'] not in members:return jsonify(error='Join the room first.'),403
        row=connection.execute('SELECT state FROM room_games WHERE room=?',(room_id,)).fetchone()
        state=json.loads(row['state']) if row else dict(board=['']*9,players={},turn='X',winner=None,revision=0)
        game=state.get('basketball',dict(players={},scores={'X':0,'O':0},turn='X',winner=None,revision=0,shot=None))
        if any(uid not in members for uid in game['players'].values()):
            game=dict(players={},scores={'X':0,'O':0},turn='X',winner=None,revision=game['revision']+1,shot=None)
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
            elif action in ('shoot','reset'):
                if not role:return jsonify(error='Join the game first.'),403
                if type(data.get('revision')) is not int or data['revision']!=game['revision']:
                    return jsonify(error='Game updated. Try again.'),409
                if action=='reset':
                    if not game['winner']:return jsonify(error='Finish this round first.'),409
                    game.update(scores={'X':0,'O':0},turn='X',winner=None,shot=None)
                else:
                    aim=data.get('aim')
                    if type(aim) not in (float,int) or not 0<=aim<=1:return jsonify(error='Invalid shot.'),400
                    if len(game['players'])!=2 or role!=game['turn'] or game['winner']:
                        return jsonify(error='Wait for your turn.'),409
                    goal=abs(aim-.5)<=.13
                    game['scores'][role]+=int(goal)
                    game['shot']=dict(id=game['revision']+1,player=role,goal=goal,aim=aim)
                    if game['scores'][role]>=5:game['winner']=role
                    else:game['turn']='O' if role=='X' else 'X'
                game['revision']+=1
            else:return jsonify(error='Unknown game action.'),400
            state['basketball']=game
            connection.execute('INSERT INTO room_games VALUES(?,?) ON CONFLICT(room) DO UPDATE SET state=excluded.state',(room_id,json.dumps(state)))
        connection.commit()
        return jsonify(**{k:v for k,v in game.items() if k!='players'},players={mark:members[uid] for mark,uid in game['players'].items()},you=role)

    @app.route('/api/rooms/<room_id>/game', methods=['GET', 'POST'])
    def room_game(room_id):
        connection=db()
        connection.execute('BEGIN IMMEDIATE')
        if not connection.execute('SELECT 1 FROM rooms WHERE id=?',(room_id,)).fetchone():
            return jsonify(error='Room not found.'),404
        members={m['id']:m['name'] for m in connection.execute('SELECT id,name FROM members WHERE room=?',(room_id,))}
        if session['uid'] not in members:
            return jsonify(error='Join the room first.'),403
        row=connection.execute('SELECT state FROM room_games WHERE room=?',(room_id,)).fetchone()
        game=json.loads(row['state']) if row else dict(board=['']*9,players={},turn='X',winner=None,revision=0)
        if any(uid not in members for uid in game['players'].values()):
            game=dict(board=['']*9,players={},turn='X',winner=None,revision=game['revision']+1)
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
            elif action in ('move','reset'):
                if not role:return jsonify(error='Join the game to play.'),403
                if data.get('revision')!=game['revision']:
                    return jsonify(error='The game changed. Try again.'),409
                if action=='reset':
                    if not game['winner']:return jsonify(error='Finish this round before starting another.'),409
                    game.update(board=['']*9,turn='X',winner=None)
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
                game['revision']+=1
            else:return jsonify(error='Unknown game action.'),400
            connection.execute('INSERT INTO room_games VALUES(?,?) ON CONFLICT(room) DO UPDATE SET state=excluded.state',(room_id,json.dumps(game)))
        connection.commit()
        return jsonify(board=game['board'],players={mark:members[uid] for mark,uid in game['players'].items()},you=role,turn=game['turn'],winner=game['winner'],revision=game['revision'])
