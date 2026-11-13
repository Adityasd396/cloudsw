"""Run once on the server: python setup_admin.py. No password is printed."""
from getpass import getpass
from pathlib import Path
from werkzeug.security import generate_password_hash


def main():
    directory=Path(__file__).resolve().parent/'instance'
    directory.mkdir(exist_ok=True)
    target=directory/'admin-password.hash'
    if target.exists():
        raise SystemExit('Admin password is already configured. Remove the hash file deliberately to rotate it.')
    password=getpass('Choose a private admin password (at least 14 characters): ')
    if len(password)<14:raise SystemExit('Use at least 14 characters.')
    if password!=getpass('Confirm password: '):raise SystemExit('Passwords did not match.')
    with target.open('x',encoding='utf-8') as output:output.write(generate_password_hash(password,method='scrypt'))
    try:target.chmod(0o600)
    except OSError:pass
    from app import app
    try:
        count=app.extensions['solace_ops']['seed_archive']()
        print(f'Copied {count} existing messages from the last 30 days into the private backup.')
    except Exception:
        print('Password saved. Historical backup could not be copied; new chats will still be backed up.')
    print('Private panel configured at /ops/solace. Reload the web app. No phone notifications are used.')


if __name__=='__main__':main()
