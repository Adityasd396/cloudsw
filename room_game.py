"""One transactional, two-player tic-tac-toe game per room."""
import json
from flask import jsonify, request, session


def register_game(app, db):
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
