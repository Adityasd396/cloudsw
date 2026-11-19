FROM python:3.13-slim
WORKDIR /app
ENV PYTHONUNBUFFERED=1 PORT=8080 COOKIE_SECURE=1
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt && useradd --uid 10001 --create-home afterglow && mkdir -p /app/instance && chown afterglow:afterglow /app/instance
COPY app.py room_game.py admin_panel.py setup_admin.py serve.py ./
COPY templates ./templates
COPY static ./static
USER afterglow
EXPOSE 8080
CMD ["python", "serve.py"]
