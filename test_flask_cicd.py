from flask_cicd import app

def test_info_route():
    tester = app.test_client()
    response = tester.get('/info')
    assert response.status_code == 200
    assert b"HELLO STRANGER" in response.data

def test_number_route():
    tester = app.test_client()
    response = tester.get('/number')
    assert response.status_code == 200
    assert b"+9122222" in response.data

