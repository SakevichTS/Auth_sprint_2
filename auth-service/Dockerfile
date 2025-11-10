FROM python:3.10

# Системный пользователь заранее, чтобы COPY сразу задавал владельца
RUN useradd -m -r -s /usr/sbin/nologin appuser

WORKDIR /app

# Базовые ENV + ускорение pip
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONPATH=/app

# Сначала зависимости — лучше кэшируются
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Копируем код сразу под appuser
COPY --chown=appuser:appuser main.py ./main.py
COPY --chown=appuser:appuser src/ ./src
COPY --chown=appuser:appuser alembic.ini ./
COPY --chown=appuser:appuser migrations/ ./migrations/

USER appuser

EXPOSE 8000
# CMD ["gunicorn", "-w", "4", "-k", "uvicorn_worker.UvicornWorker", "main:app", "--bind", "0.0.0.0:8000"]
CMD ["sh", "-c", "sleep 10 && alembic upgrade head && exec gunicorn -w 4 -k uvicorn_worker.UvicornWorker main:app --bind 0.0.0.0:8000"]