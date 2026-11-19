"""Shared agreement for room games; never touches playback or chat tables."""
def agree(game,role,values=None):
    key='rematch_votes' if values is None else 'proposal'
    if values is None:
        votes=game.setdefault(key,[])
    else:
        if game.get(key,{}).get('values')!=values:game[key]={'values':values,'votes':[]}
        votes=game[key]['votes']
    if role not in votes:votes.append(role)
    ready=len(game['players'])>=2 and all(p in votes for p in game['players'])
    if ready:game.pop(key,None)
    return ready


def cheer(game,role,emoji):
    import time,secrets
    if emoji not in ('🫶','✨','👏'):raise ValueError('Choose a cheer.')
    if time.time()-game.get('cheer',{}).get('created',0)<1:raise ValueError('Give that cheer a moment.')
    game['cheer']={'id':secrets.token_hex(8),'player':role,'emoji':emoji,'created':time.time()}
