FROM python:3.10-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \ 
    PYTHONPATH=/

WORKDIR /tests

COPY functional/requirements.txt functional/requirements.txt

RUN pip install -U pip && pip install --no-cache-dir -r functional/requirements.txt

COPY . .

CMD ["pytest", "functional/src", "-q"]