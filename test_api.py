import sys
from fastapi.testclient import TestClient

sys.path.append(".")
from main import app

client = TestClient(app)

def print_banner(title: str):
    print("=" * 70)
    print(f" {title.upper()} ".center(70, "="))
    print("=" * 70)

def test_all():
    # =========================================================================
    # AUTH: REGISTER & LOGIN
    # =========================================================================
    print_banner("1. POST /register - Register New User")
    reg_payload = {"username": "testuser", "password": "testpass123"}
    response = client.post("/register", json=reg_payload)
    print(f"Response (Status {response.status_code}): {response.json()}")
    # Allow 400 if already registered (re-runs)
    assert response.status_code in (201, 400)

    print_banner("2. POST /token - Login and Get JWT Token")
    response = client.post("/token", data={"username": "testuser", "password": "testpass123"})
    print(f"Response (Status {response.status_code}): {response.json()}")
    assert response.status_code == 200
    token = response.json()["access_token"]
    auth_headers = {"Authorization": f"Bearer {token}"}
    print(f"  [OK] JWT Token received.")

    print_banner("3. GET /users - List All Users")
    response = client.get("/users")
    print(f"Response (Status {response.status_code}):")
    for u in response.json():
        print(f"  - User ID {u['id']}: {u['username']} (active={u['is_active']})")
    assert response.status_code == 200

    print_banner("4. GET /users/me - Get Current Authenticated User")
    response = client.get("/users/me", headers=auth_headers)
    print(f"Response (Status {response.status_code}): {response.json()}")
    assert response.status_code == 200
    assert response.json()["username"] == "testuser"

    # =========================================================================
    # WORKOUTS: CREATE, LIST, GET, UPDATE, DELETE
    # =========================================================================
    print_banner("5. POST /workouts - Log New Workouts")
    w1 = client.post("/workouts", json={"user_id": 1, "activity_type": "Running", "duration_minutes": 30, "calories_burned": 350})
    w2 = client.post("/workouts", json={"user_id": 1, "activity_type": "Yoga",    "duration_minutes": 45, "calories_burned": 150})
    print(f"Workout 1 (Status {w1.status_code}): {w1.json()}")
    print(f"Workout 2 (Status {w2.status_code}): {w2.json()}")
    assert w1.status_code == 201
    assert w2.status_code == 201
    workout_id = w1.json()["id"]

    print_banner("6. GET /workouts - List All Workouts")
    response = client.get("/workouts")
    print(f"Response (Status {response.status_code}): {len(response.json())} workouts")
    assert response.status_code == 200

    print_banner("7. GET /workouts?activity_type=Running - Filter Workouts")
    response = client.get("/workouts?activity_type=Running")
    print(f"Response (Status {response.status_code}):")
    for w in response.json():
        print(f"  - [{w['id']}] {w['activity_type']} {w['duration_minutes']}min {w['calories_burned']}kcal")
    assert response.status_code == 200
    assert all(w["activity_type"] == "Running" for w in response.json())

    print_banner(f"8. GET /workouts/{workout_id} - Get Single Workout")
    response = client.get(f"/workouts/{workout_id}")
    print(f"Response (Status {response.status_code}): {response.json()}")
    assert response.status_code == 200
    assert response.json()["id"] == workout_id

    print_banner(f"9. PUT /workouts/{workout_id} - Update Workout")
    update_payload = {"activity_type": "Cycling", "duration_minutes": 60, "calories_burned": 500}
    response = client.put(f"/workouts/{workout_id}", json=update_payload)
    print(f"Response (Status {response.status_code}): {response.json()}")
    assert response.status_code == 200
    assert response.json()["activity_type"] == "Cycling"
    assert response.json()["duration_minutes"] == 60

    print_banner(f"10. DELETE /workouts/{workout_id} - Delete Workout")
    response = client.delete(f"/workouts/{workout_id}")
    print(f"Response (Status {response.status_code}): Deleted workout ID {workout_id}")
    assert response.status_code == 204

    verify = client.get(f"/workouts/{workout_id}")
    print(f"Verify deletion (Status {verify.status_code}): {verify.json()['detail']}")
    assert verify.status_code == 404

    # =========================================================================
    # GOALS: CREATE, LIST, GET, UPDATE, DELETE
    # =========================================================================
    print_banner("11. POST /goals - Set Goals")
    g1 = client.post("/goals", json={"user_id": 1, "goal_type": "calories", "target_value": 500})
    g2 = client.post("/goals", json={"user_id": 1, "goal_type": "duration", "target_value": 90})
    print(f"Goal 1 (Status {g1.status_code}): {g1.json()}")
    print(f"Goal 2 (Status {g2.status_code}): {g2.json()}")
    assert g1.status_code == 201
    assert g2.status_code == 201
    goal_id = g1.json()["id"]

    print_banner("12. GET /goals - List All Goals")
    response = client.get("/goals")
    print(f"Response (Status {response.status_code}): {len(response.json())} goals")
    assert response.status_code == 200

    print_banner("13. GET /goals?user_id=1 - Filter Goals by User")
    response = client.get("/goals?user_id=1")
    print(f"Response (Status {response.status_code}):")
    for g in response.json():
        print(f"  - [{g['id']}] {g['goal_type']} target={g['target_value']}")
    assert response.status_code == 200

    print_banner(f"14. GET /goals/{goal_id} - Get Single Goal")
    response = client.get(f"/goals/{goal_id}")
    print(f"Response (Status {response.status_code}): {response.json()}")
    assert response.status_code == 200

    print_banner(f"15. PUT /goals/{goal_id} - Update Goal")
    response = client.put(f"/goals/{goal_id}", json={"target_value": 800})
    print(f"Response (Status {response.status_code}): {response.json()}")
    assert response.status_code == 200
    assert response.json()["target_value"] == 800

    print_banner(f"16. DELETE /goals/{goal_id} - Delete Goal")
    response = client.delete(f"/goals/{goal_id}")
    print(f"Response (Status {response.status_code}): Deleted goal ID {goal_id}")
    assert response.status_code == 204

    verify = client.get(f"/goals/{goal_id}")
    print(f"Verify deletion (Status {verify.status_code}): {verify.json()['detail']}")
    assert verify.status_code == 404

    # =========================================================================
    # PROGRESS
    # =========================================================================
    print_banner("17. GET /progress/1 - Check User Progress")
    response = client.get("/progress/1")
    print(f"Response (Status {response.status_code}):")
    summary = response.json()
    print(f"  Date: {summary['date']}")
    print(f"  Total Workouts : {summary['total_workouts']}")
    print(f"  Total Duration : {summary['total_duration_minutes']} min")
    print(f"  Total Calories : {summary['total_calories_burned']} kcal")
    print(f"  Goals Progress : {len(summary['goals'])} goal(s)")
    assert response.status_code == 200

    print_banner("ALL 17 ENDPOINTS PASSED SUCCESSFULLY!")

if __name__ == "__main__":
    test_all()
