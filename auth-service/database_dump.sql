-- включаем расширение для генерации UUID, если ещё нет
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- Добавляем роли, только если их ещё нет
INSERT INTO roles (id, name, description)
VALUES
  (gen_random_uuid(), 'user', 'Базовая роль'),
  (gen_random_uuid(), 'subscriber', 'Подписка: новые фильмы'),
  (gen_random_uuid(), 'admin', 'Админ-доступ')
ON CONFLICT (name) DO NOTHING;