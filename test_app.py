import os
import tempfile
import pytest
from app import app, init_db, analyze_sentiment

@pytest.fixture
def client():
    fd, path = tempfile.mkstemp()
    os.close(fd)
    app.config.update(TESTING=True, DATABASE=path, SECRET_KEY='test-secret')
    with app.app_context():
        init_db()
    with app.test_client() as client:
        yield client
    os.unlink(path)

def test_sentiment():
    assert analyze_sentiment('I love this excellent product!')[0] == 'Positive'
    assert analyze_sentiment('This is terrible and disappointing.')[0] == 'Negative'
    assert analyze_sentiment('The product is a table.')[0] == 'Neutral'

def test_register_login(client):
    response=client.post('/register',data={'username':'tester','email':'tester@example.com','password':'secret123','confirm_password':'secret123'},follow_redirects=True)
    assert b'Account created successfully' in response.data
    response=client.post('/login',data={'identifier':'tester','password':'secret123'},follow_redirects=True)
    assert b'Analytics Dashboard' in response.data
