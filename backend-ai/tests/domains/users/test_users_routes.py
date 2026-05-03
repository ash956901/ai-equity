"""Unit tests for users domain routes (post-Round-2 auth gate)."""

from uuid import uuid4

from src.domains.users import routes as user_routes


class _DummyUsersService:
    def __init__(self, db):
        self.db = db

    def get_user_profile(self, user_id):
        return {"id": str(user_id), "email": "demo@example.com"}

    def update_user_profile(self, user_id, update_data):
        return {"id": str(user_id), **update_data}

    async def upload_profile_pic(self, user_id, file):
        return {"profile_pic_url": f"/uploads/avatars/{user_id}.png"}

    def submit_kyc(self, user_id, pan_card_number, aadhaar_number):
        return {
            "user_id": str(user_id),
            "kyc_status": "pending",
            "pan": pan_card_number,
            "aadhaar": aadhaar_number,
        }

    def get_kyc_status(self, user_id):
        return {"user_id": str(user_id), "kyc_status": "pending"}

    def verify_kyc(self, user_id):
        return {"user_id": str(user_id), "kyc_status": "verified"}


def test_update_user_profile_route(monkeypatch, make_authed_client, fake_user):
    monkeypatch.setattr(user_routes, "UsersService", _DummyUsersService)
    client = make_authed_client(router=user_routes.router, user=fake_user)

    response = client.put(
        f"/users/{fake_user.id}",
        json={"full_name": "Demo User", "expertise_level": "advanced"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["id"] == str(fake_user.id)
    assert body["full_name"] == "Demo User"
    assert body["expertise_level"] == "advanced"


def test_submit_kyc_route(monkeypatch, make_authed_client, fake_user):
    monkeypatch.setattr(user_routes, "UsersService", _DummyUsersService)
    client = make_authed_client(router=user_routes.router, user=fake_user)

    response = client.post(
        f"/users/{fake_user.id}/kyc/submit",
        json={"pan_card_number": "ABCDE1234F", "aadhaar_number": "123412341234"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["user_id"] == str(fake_user.id)
    assert body["kyc_status"] == "pending"


def test_verify_kyc_route(monkeypatch, make_authed_client, fake_user):
    monkeypatch.setattr(user_routes, "UsersService", _DummyUsersService)
    client = make_authed_client(router=user_routes.router, user=fake_user)

    response = client.post(f"/users/{fake_user.id}/kyc/verify")

    assert response.status_code == 200
    body = response.json()
    assert body["user_id"] == str(fake_user.id)
    assert body["kyc_status"] == "verified"


def test_assert_self_blocks_cross_account(monkeypatch, make_authed_client, fake_user):
    """The auth gate must 403 when path user_id != current_user.id."""
    monkeypatch.setattr(user_routes, "UsersService", _DummyUsersService)
    client = make_authed_client(router=user_routes.router, user=fake_user)
    other = uuid4()

    response = client.get(f"/users/{other}")

    assert response.status_code == 403
    assert "Cannot access another user's resource" in response.text
