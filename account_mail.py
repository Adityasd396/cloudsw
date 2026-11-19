"""Optional SMTP email ownership verification and one-use password recovery."""
import hashlib
import os
import re
import secrets
import smtplib
import time
from email.message import EmailMessage
from flask import g,jsonify,render_template,request,session
from werkzeug.security import generate_password_hash


def register_account_mail(app,db,config,public_url,limited,require_account):
    def mail_ready():
        return bool(config('SOLACE_SMTP_HOST') and config('SOLACE_MAIL_FROM') and public_url())

    def deliver(owner,email,purpose):
        token=secrets.token_urlsafe(40);now=time.time()
        db().execute('DELETE FROM account_tokens WHERE owner=? AND purpose=?',(owner,purpose))
        db().execute('INSERT INTO account_tokens VALUES(?,?,?,?,?)',(hashlib.sha256(token.encode()).hexdigest(),owner,purpose,now+(1800 if purpose=='reset' else 86400),now))
        db().execute('DELETE FROM account_tokens WHERE expires<?',(now,));db().commit()
        route='/reset-password' if purpose=='reset' else '/verify-email'
        message=EmailMessage();message['Subject']='Reset your Solace password' if purpose=='reset' else 'Verify your Solace email'
        sender=str(config('SOLACE_MAIL_FROM'))
        if not re.fullmatch(r'[^\s@<>]+@[^\s@<>]+',sender):raise ValueError('Invalid sender configuration')
        message['From']=sender;message['To']=email
        message.set_content(('Reset your password' if purpose=='reset' else 'Confirm your email address')+' using this one-use link:\n\n'+public_url()+route+'#token='+token+'\n\n'+('Expires in 30 minutes.' if purpose=='reset' else 'Expires in 24 hours.')+' If you did not request this, you can ignore this email. Never share this link or your password.')
        host=str(config('SOLACE_SMTP_HOST'));port=int(config('SOLACE_SMTP_PORT','587'))
        if not 1<=port<=65535:raise ValueError('Invalid SMTP port')
        import ssl
        context=ssl.create_default_context()
        use_ssl=str(config('SOLACE_SMTP_SSL','0'))=='1'
        client=smtplib.SMTP_SSL(host,port,timeout=5,context=context) if use_ssl else smtplib.SMTP(host,port,timeout=5)
        with client:
            if not use_ssl:client.starttls(context=context)
            username=str(config('SOLACE_SMTP_USERNAME'));password=str(config('SOLACE_SMTP_PASSWORD'))
            if username:client.login(username,password)
            client.send_message(message)

    def send_safely(owner,email,purpose):
        try:deliver(owner,email,purpose);return True
        except (OSError,ValueError,smtplib.SMTPException):
            # No email, URL, token or exception body in logs.
            app.logger.warning('account_mail_delivery_failed request_id=%s purpose=%s',getattr(g,'request_id','unknown'),purpose)
            return False

    @app.get('/reset-password')
    @app.get('/verify-email')
    def email_action_page():
        return render_template('email-action.html',recovery=request.path=='/reset-password')

    @app.post('/api/auth/recovery')
    def recovery_request():
        if not mail_ready():return jsonify(error='Email recovery is not configured. Contact the operator for account support.'),503
        if limited('recovery',4,3600):return jsonify(error='Too many recovery requests. Try again later.'),429
        email=str((request.get_json(silent=True) or {}).get('email','')).strip().casefold()
        if len(email)>254 or not re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+',email):return jsonify(error='Enter a valid email address.'),400
        row=db().execute('SELECT id FROM accounts WHERE email=?',(email,)).fetchone()
        if row:send_safely(row['id'],email,'reset')
        return jsonify(ok=True,message='If this email has an account, a recovery link will arrive. Check spam, or contact the operator if it does not arrive.')

    @app.post('/api/auth/send-verification')
    def verification_request():
        account=require_account()
        if not mail_ready():return jsonify(error='Email verification is not configured yet.'),503
        if limited('verification',4,3600):return jsonify(error='Please wait before requesting another email.'),429
        if account['verified']:return jsonify(ok=True,message='Your email is already verified.')
        if not send_safely(account['id'],account['email'],'verify'):return jsonify(error='Email delivery is temporarily unavailable. Please try again later.'),503
        return jsonify(ok=True,message='Verification email sent. Check your inbox and spam folder.')

    @app.post('/api/auth/reset')
    @app.post('/api/auth/verify')
    def redeem():
        if limited('email-token',15):return jsonify(error='Too many attempts. Try again later.'),429
        data=request.get_json(silent=True) or {};token=data.get('token','');purpose='reset' if request.path.endswith('/reset') else 'verify'
        if not isinstance(token,str) or not re.fullmatch(r'[A-Za-z0-9_-]{40,100}',token):return jsonify(error='This link is invalid or expired. Request a new one.'),400
        password=data.get('password','')
        if purpose=='reset' and (not isinstance(password,str) or not 12<=len(password)<=128):return jsonify(error='Use a password between 12 and 128 characters.'),400
        digest=hashlib.sha256(token.encode()).hexdigest();now=time.time()
        db().execute('BEGIN IMMEDIATE')
        row=db().execute('SELECT * FROM account_tokens WHERE token=? AND purpose=? AND expires>?',(digest,purpose,now)).fetchone()
        if not row or not db().execute('SELECT 1 FROM accounts WHERE id=?',(row['owner'],)).fetchone():
            db().rollback();return jsonify(error='This link is invalid or expired. Request a new one.'),400
        if purpose=='reset':
            db().execute('UPDATE accounts SET password=?,verified=1 WHERE id=?',(generate_password_hash(password,method='scrypt'),row['owner']))
            db().execute('DELETE FROM account_sessions WHERE owner=?',(row['owner'],))
            if getattr(g,'account',None) and g.account['id']==row['owner']:
                session.pop('account_uid',None);session['uid']=secrets.token_urlsafe(24);session['account_csrf']=secrets.token_urlsafe(32)
            db().execute('DELETE FROM account_tokens WHERE owner=?',(row['owner'],))
        else:
            db().execute('UPDATE accounts SET verified=1 WHERE id=?',(row['owner'],));db().execute('DELETE FROM account_tokens WHERE token=?',(digest,))
        db().commit();response=jsonify(ok=True,message='Password updated. Sign in with your new password.' if purpose=='reset' else 'Your email is verified.')
        if purpose=='reset':response.delete_cookie('solace_account')
        return response

    return {'ready':mail_ready,'send':send_safely}
