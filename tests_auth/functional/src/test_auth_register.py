import pytest

from tests.functional.settings import test_settings

pytestmark = pytest.mark.asyncio

@pytest.mark.parametrize(
    "login,email,password",
    [
        ("user1", "user1@example.com", "secret123"),
        ("user2", "user2@example.com", "secret123"),
        ("user3", "user3@example.com", "secret123"),
    ],
)
async def test_register_users(make_post_request, login, email, password):
    payload = {
        "login": login,
        "email": email,
        "password": password,
        "first_name": "Test",
        "last_name": "User",
    }

    response = await make_post_request("/auth/register", payload)

    assert response["status"] == 201
    body = response["body"]
    assert "id" in body
    assert body["login"] == login
    assert body["email"] == email