from copy import deepcopy

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from src import app as app_module


@pytest.fixture
def client():
    return TestClient(app_module.app)


@pytest.fixture(autouse=True)
def reset_activities():
    original_activities = deepcopy(app_module.activities)
    yield
    app_module.activities.clear()
    app_module.activities.update(deepcopy(original_activities))


# Integration tests (AAA)
def test_get_root_redirects_to_static_index(client):
    # Arrange
    path = "/"

    # Act
    response = client.get(path, follow_redirects=False)

    # Assert
    assert response.status_code == 307
    assert response.headers["location"] == "/static/index.html"


def test_get_activities_returns_seeded_data(client):
    # Arrange
    path = "/activities"

    # Act
    response = client.get(path)

    # Assert
    assert response.status_code == 200
    payload = response.json()
    assert isinstance(payload, dict)
    assert "Chess Club" in payload
    assert "participants" in payload["Chess Club"]


def test_signup_adds_participant_successfully(client):
    # Arrange
    activity = "Chess Club"
    email = "new.student@mergington.edu"

    # Act
    response = client.post(f"/activities/{activity}/signup", params={"email": email})

    # Assert
    assert response.status_code == 200
    assert response.json()["message"] == f"Signed up {email} for {activity}"
    assert email in app_module.activities[activity]["participants"]


def test_signup_duplicate_participant_returns_400(client):
    # Arrange
    activity = "Chess Club"
    email = app_module.activities[activity]["participants"][0]

    # Act
    response = client.post(f"/activities/{activity}/signup", params={"email": email})

    # Assert
    assert response.status_code == 400
    assert response.json()["detail"] == "Student already signed up for this activity"


def test_signup_unknown_activity_returns_404(client):
    # Arrange
    activity = "Unknown Club"
    email = "student@mergington.edu"

    # Act
    response = client.post(f"/activities/{activity}/signup", params={"email": email})

    # Assert
    assert response.status_code == 404
    assert response.json()["detail"] == "Activity not found"


def test_unregister_removes_participant_successfully(client):
    # Arrange
    activity = "Chess Club"
    email = app_module.activities[activity]["participants"][0]

    # Act
    response = client.delete(f"/activities/{activity}/participants", params={"email": email})

    # Assert
    assert response.status_code == 200
    assert response.json()["message"] == f"Removed {email} from {activity}"
    assert email not in app_module.activities[activity]["participants"]


def test_unregister_unknown_activity_returns_404(client):
    # Arrange
    activity = "Unknown Club"
    email = "student@mergington.edu"

    # Act
    response = client.delete(f"/activities/{activity}/participants", params={"email": email})

    # Assert
    assert response.status_code == 404
    assert response.json()["detail"] == "Activity not found"


def test_unregister_missing_participant_returns_404(client):
    # Arrange
    activity = "Chess Club"
    email = "missing.student@mergington.edu"

    # Act
    response = client.delete(f"/activities/{activity}/participants", params={"email": email})

    # Assert
    assert response.status_code == 404
    assert response.json()["detail"] == "Participant not found in this activity"


def test_state_transition_signup_then_unregister(client):
    # Arrange
    activity = "Debate Club"
    email = "flow.student@mergington.edu"

    # Act
    signup_response = client.post(f"/activities/{activity}/signup", params={"email": email})
    unregister_response = client.delete(
        f"/activities/{activity}/participants", params={"email": email}
    )

    # Assert
    assert signup_response.status_code == 200
    assert unregister_response.status_code == 200
    assert email not in app_module.activities[activity]["participants"]


def test_state_transition_unregister_twice_returns_404_second_time(client):
    # Arrange
    activity = "Programming Class"
    email = app_module.activities[activity]["participants"][0]

    # Act
    first_response = client.delete(f"/activities/{activity}/participants", params={"email": email})
    second_response = client.delete(f"/activities/{activity}/participants", params={"email": email})

    # Assert
    assert first_response.status_code == 200
    assert second_response.status_code == 404
    assert second_response.json()["detail"] == "Participant not found in this activity"


def test_signup_accepts_empty_email_current_contract(client):
    # Arrange
    activity = "Science Club"
    email = ""

    # Act
    response = client.post(f"/activities/{activity}/signup", params={"email": email})

    # Assert
    assert response.status_code == 200
    assert email in app_module.activities[activity]["participants"]


def test_signup_accepts_whitespace_email_current_contract(client):
    # Arrange
    activity = "Science Club"
    email = "   "

    # Act
    response = client.post(f"/activities/{activity}/signup", params={"email": email})

    # Assert
    assert response.status_code == 200
    assert email in app_module.activities[activity]["participants"]


def test_signup_accepts_malformed_email_current_contract(client):
    # Arrange
    activity = "Science Club"
    email = "not-an-email"

    # Act
    response = client.post(f"/activities/{activity}/signup", params={"email": email})

    # Assert
    assert response.status_code == 200
    assert email in app_module.activities[activity]["participants"]


# Direct unit tests (AAA)
def test_root_handler_returns_redirect_response():
    # Arrange
    expected_location = "/static/index.html"

    # Act
    response = app_module.root()

    # Assert
    assert response.status_code == 307
    assert response.headers["location"] == expected_location


def test_get_activities_handler_returns_activities_reference():
    # Arrange
    expected = app_module.activities

    # Act
    response = app_module.get_activities()

    # Assert
    assert response is expected


def test_signup_handler_adds_participant_direct_call():
    # Arrange
    activity = "Art Studio"
    email = "direct.student@mergington.edu"

    # Act
    result = app_module.signup_for_activity(activity, email)

    # Assert
    assert result["message"] == f"Signed up {email} for {activity}"
    assert email in app_module.activities[activity]["participants"]


def test_signup_handler_duplicate_raises_http_exception():
    # Arrange
    activity = "Music Band"
    email = app_module.activities[activity]["participants"][0]

    # Act / Assert
    with pytest.raises(HTTPException) as exc:
        app_module.signup_for_activity(activity, email)

    assert exc.value.status_code == 400
    assert exc.value.detail == "Student already signed up for this activity"


def test_signup_handler_unknown_activity_raises_http_exception():
    # Arrange
    activity = "Unknown Club"
    email = "student@mergington.edu"

    # Act / Assert
    with pytest.raises(HTTPException) as exc:
        app_module.signup_for_activity(activity, email)

    assert exc.value.status_code == 404
    assert exc.value.detail == "Activity not found"


def test_unregister_handler_removes_participant_direct_call():
    # Arrange
    activity = "Gym Class"
    email = app_module.activities[activity]["participants"][0]

    # Act
    result = app_module.unregister_participant(activity, email)

    # Assert
    assert result["message"] == f"Removed {email} from {activity}"
    assert email not in app_module.activities[activity]["participants"]


def test_unregister_handler_unknown_activity_raises_http_exception():
    # Arrange
    activity = "Unknown Club"
    email = "student@mergington.edu"

    # Act / Assert
    with pytest.raises(HTTPException) as exc:
        app_module.unregister_participant(activity, email)

    assert exc.value.status_code == 404
    assert exc.value.detail == "Activity not found"


def test_unregister_handler_missing_participant_raises_http_exception():
    # Arrange
    activity = "Gym Class"
    email = "missing.student@mergington.edu"

    # Act / Assert
    with pytest.raises(HTTPException) as exc:
        app_module.unregister_participant(activity, email)

    assert exc.value.status_code == 404
    assert exc.value.detail == "Participant not found in this activity"
