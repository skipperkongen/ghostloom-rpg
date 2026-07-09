def test_register_and_login(client):
    register = client.post(
        "/auth/register",
        json={
            "email": "player@example.com",
            "password": "securepass",
            "display_name": "Player One",
        },
    )
    assert register.status_code == 201
    assert "access_token" in register.json()

    login = client.post(
        "/auth/login",
        json={"email": "player@example.com", "password": "securepass"},
    )
    assert login.status_code == 200
    token = login.json()["access_token"]

    me = client.get("/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200
    assert me.json()["email"] == "player@example.com"
    assert me.json()["display_name"] == "Player One"
