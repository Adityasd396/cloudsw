"""Build and verify public release files only. Never package instance or credentials."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil
import zipfile

ROOT=Path(__file__).resolve().parents[1]
SERVER={'app.py','room_game.py','admin_panel.py','setup_admin.py','requirements.txt','PYTHONANYWHERE.md','ADMIN-SETUP.md','DEPLOYMENT-RELIABILITY.md','release.json','tools/storage.py','tools/verify_deployment.py'}

def build(version):
    if not re.fullmatch(r'[0-9A-Za-z._-]{1,40}',version):raise ValueError('Invalid version')
    release=(ROOT/'release').resolve()
    if release.parent!=ROOT:raise ValueError('Unsafe release directory')
    # A fresh release must be complete even if its old manifest was removed.
    names=set(SERVER)
    names.update(['README.md','RELEASE-NOTES.md','DEPLOYMENT.md','Dockerfile','.dockerignore','run.py','serve.py','run_mobile_server.py','launch_mobile.py','start.bat','start-mobile.bat'])
    names.update(path.relative_to(ROOT).as_posix() for pattern in ['*.tsx','*.cjs','*.json','app.config.js','index.js','README.md','.easignore','scripts/*.cjs'] for path in (ROOT/'mobile').glob(pattern) if path.is_file())
    names.update(['HARDENING-REPORT.md','DEPLOYMENT-RELIABILITY.md','release.json','tools/storage.py','tools/build_release.py','tools/verify_deployment.py','mobile/transport.cjs','mobile/game-bridge.cjs','mobile/gestures.cjs','mobile/CuteGesture.tsx','solace-v2-watch.jpg','solace-v2-queue.jpg','solace-v2-room.jpg','solace-v2-keyboard.jpg','solace-v2-search-landscape.jpg'])
    names.add('mobile/GestureComposer.tsx')
    names.add('mobile/ClientDiagnostics.tsx')
    for folder,pattern in [('static','**/*'),('templates','**/*'),('tests','*.py'),('mobile/tests','*.test.cjs')]:
        names.update(path.relative_to(ROOT).as_posix() for path in (ROOT/folder).glob(pattern) if path.is_file() and '__pycache__' not in path.parts)
    for template in ['templates/index.html','templates/admin.html','templates/admin-login.html','static/game.html','static/tictactoe.html']:
        path=ROOT/template
        source=path.read_text(encoding='utf-8')
        source=re.sub(r'<meta name="solace-release" content="[^"]*">','',source)
        source=source.replace('</head>','<meta name="solace-release" content="'+version+'"></head>')
        source=re.sub(r'(/static/[^"?]+)(?:\?v=[^"&]+)?(?=")',lambda match:match[1]+'?v='+version,source)
        path.write_text(source,encoding='utf-8')
    digest=hashlib.sha256()
    for name in sorted(names-{'release.json'}):
        path=ROOT/name
        if not path.is_file():raise ValueError('Missing public release file: '+name)
        digest.update(name.encode());digest.update(path.read_bytes())
    (ROOT/'release.json').write_text(json.dumps({'version':version,'build':digest.hexdigest()[:16]},indent=2)+'\n',encoding='utf-8')
    manifest={}
    for name in sorted(names):
        source=(ROOT/name).resolve();target=(release/name).resolve()
        if not source.is_relative_to(ROOT) or not target.is_relative_to(release):raise ValueError('Unsafe release path')
        if any(part in {'instance','.git','node_modules','__pycache__','.expo','.openai'} or part.startswith('.export-') for part in Path(name).parts):raise ValueError('Private/generated path in release')
        if source.suffix in {'.db','.key','.hash'} or source.name.startswith('.env'):raise ValueError('Credential/storage file in release')
        target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(source,target);manifest[name]=hashlib.sha256(source.read_bytes()).hexdigest()
    (release/'MANIFEST.json').write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8')
    results={}
    for suffix,files in [('release-source.zip',names|{'MANIFEST.json'}),('pythonanywhere.zip',{n for n in names if n in SERVER or n.startswith(('static/','templates/'))})]:
        destination=ROOT/('Solace-'+suffix)
        with zipfile.ZipFile(destination,'w',zipfile.ZIP_DEFLATED,compresslevel=9) as archive:
            for name in sorted(files):
                info=zipfile.ZipInfo(name,date_time=(2026,11,14,0,0,0));info.compress_type=zipfile.ZIP_DEFLATED;info.external_attr=0o644<<16
                archive.writestr(info,(release/name).read_bytes(),compresslevel=9)
        with zipfile.ZipFile(destination) as archive:
            if archive.testzip() is not None or set(archive.namelist())!=files:raise ValueError('Archive integrity failed')
            for name in files:
                if archive.read(name)!=(release/name).read_bytes():raise ValueError('Archive/source mismatch')
        shutil.copyfile(destination,ROOT/('Afterglow-'+suffix));results[destination.name]={'files':len(files),'bytes':destination.stat().st_size,'sha256':hashlib.sha256(destination.read_bytes()).hexdigest()}
    for name,value in manifest.items():
        if hashlib.sha256((ROOT/name).read_bytes()).hexdigest()!=value:raise ValueError('Source changed during packaging')
    return {'release':json.loads((ROOT/'release.json').read_text()),'archives':results,'private_files_excluded':True}

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--version',default='2026.11.14.1');args=parser.parse_args();print(json.dumps(build(args.version),indent=2))
