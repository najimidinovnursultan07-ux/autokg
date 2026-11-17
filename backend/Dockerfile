FROM python:3.14-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN addgroup --system --gid 10001 autokg \
    && adduser --system --uid 10001 --ingroup autokg autokg \
    && mkdir -p /app/media /app/staticfiles \
    && chown -R autokg:autokg /app/media /app/staticfiles

USER autokg

EXPOSE 8000

CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "3", "--access-logfile", "-", "--error-logfile", "-"]
