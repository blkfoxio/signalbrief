FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

# WeasyPrint runtime dependencies (pango/glib/harfbuzz/fontconfig + default fonts).
RUN apt-get update && apt-get install -y --no-install-recommends \
        libpango-1.0-0 \
        libpangoft2-1.0-0 \
        libharfbuzz0b \
        libglib2.0-0 \
        libfontconfig1 \
        libfreetype6 \
        shared-mime-info \
        fonts-liberation \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt ./
RUN pip install -r requirements.txt

COPY . .

CMD python manage.py collectstatic --noinput \
 && python manage.py migrate --noinput \
 && gunicorn signalbrief.asgi:application -k uvicorn.workers.UvicornWorker -w 2 -b 0.0.0.0:$PORT
