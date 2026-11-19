FROM python:3.13-slim
WORKDIR /app
ENV PYTHONUNBUFFERED=1 PORT=8080 COOKIE_SECURE=1 SOLACE_ENV=production
COPY requirements.txt ./
COPY requirements.lock ./
RUN pip install --no-cache-dir -r requirements.lock && useradd --uid 10001 --create-home afterglow && mkdir -p /app/instance && chown afterglow:afterglow /app/instance
COPY app.py launch.py social.py community.py messaging.py people.py platform_safety.py staff_auth.py setup_staff.py account_mail.py user_storage.py production.py room_game.py ludo_game.py game_options.py admin_panel.py setup_admin.py serve.py release.json ./
COPY templates ./templates
COPY static ./static
USER afterglow
EXPOSE 8080
CMD ["python", "serve.py"]
