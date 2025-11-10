-- Включаем расширение для генерации UUID, если ещё нет
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- Создаём таблицу roles, если она отсутствует
CREATE TABLE IF NOT EXISTS roles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(50) UNIQUE NOT NULL,
    description TEXT
);

-- Добавляем роли, только если их ещё нет
INSERT INTO roles (id, name, description)
VALUES
  (gen_random_uuid(), 'user', 'Базовая роль'),
  (gen_random_uuid(), 'subscriber', 'Подписка: новые фильмы'),
  (gen_random_uuid(), 'admin', 'Админ-доступ')
ON CONFLICT (name) DO NOTHING;