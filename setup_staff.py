"""Owner-operated named staff enrollment. Never run automatically or from HTTP."""
import argparse
from getpass import getpass
from urllib.parse import quote
def main():
    parser=argparse.ArgumentParser();parser.add_argument('username');parser.add_argument('--role',choices=['administrator','moderator','operations'],default='administrator');args=parser.parse_args();password=getpass('New individual staff password (14–128 characters): ')
    if password!=getpass('Confirm staff password: '):raise SystemExit('Passwords did not match.')
    from app import app
    with app.app_context():identifier,secret=app.extensions['solace_staff']['create'](args.username,password,args.role)
    print('Staff identity created. Keep this authenticator enrollment secret private; it is shown only by this local setup command.')
    print('otpauth://totp/'+quote('Solace:'+args.username)+'?secret='+secret+'&issuer=Solace&algorithm=SHA1&digits=6&period=30')
    print('Enroll this identity in your authenticator, then use the existing /ops/solace login. Named staff enrollment disables shared-password bootstrap access. No phone notifications are sent.')
if __name__=='__main__':main()
