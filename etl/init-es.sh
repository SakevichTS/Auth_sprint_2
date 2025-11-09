#!/bin/sh
# Скрипт для идемпотентного создания индексов в Elasticsearch

set -euo pipefail
IFS=$(printf '\n\t')

ES=http://elasticsearch:9200

echo "[init-es] Checking ES at: $ES"

# Ждём, пока Elasticsearch не станет доступен
until curl -s --fail "$ES/_cluster/health?wait_for_status=yellow&timeout=2s" > /dev/null; do
  echo "Waiting for Elasticsearch..."
  sleep 2
done

create_index() {
  NAME=$1
  FILE=$2

  if [ ! -f "$FILE" ]; then
    echo "[init-es] ERROR: file not found: $FILE" >&2
    exit 1
  fi

  if curl -s --head --fail "$ES/$NAME" > /dev/null; then
    echo "Index '$NAME' already exists. Skipping."
  else
    echo "Index '$NAME' not found. Creating..."
    curl -X PUT "$ES/$NAME" -H "Content-Type: application/json" --data-binary "@$FILE" --fail-with-body
  fi
}

create_index movies /app/schemas/es_movies.json
create_index genres /app/schemas/es_genres.json
create_index person /app/schemas/es_person.json

echo "[init-es] Done."