import json

from fastapi.testclient import TestClient

from dual_lobe_crewai import webapp


def _client(monkeypatch, seen):
    async def fake_chat(req):
        seen.append(req)
        return {"answer": "hello from dual-lobe"}

    monkeypatch.setattr(webapp, "chat", fake_chat)
    return TestClient(webapp.app)


def test_models_lists_this_service(monkeypatch):
    client = _client(monkeypatch, [])
    body = client.get("/v1/models").json()
    assert body["object"] == "list"
    assert body["data"][0]["id"] == webapp.MODEL_ID


def test_chat_completion_returns_openai_shape(monkeypatch):
    seen = []
    client = _client(monkeypatch, seen)
    body = client.post("/v1/chat/completions", json={
        "model": "dual-lobe",
        "messages": [{"role": "system", "content": "Be brief."}, {"role": "user", "content": "Hi"}],
    }).json()
    assert body["object"] == "chat.completion"
    assert body["choices"][0]["message"] == {"role": "assistant", "content": "hello from dual-lobe"}
    assert body["choices"][0]["finish_reason"] == "stop"
    assert "Hi" in seen[0].message


def test_streaming_ends_with_done(monkeypatch):
    client = _client(monkeypatch, [])
    text = client.post("/v1/chat/completions", json={
        "messages": [{"role": "user", "content": "Hi"}], "stream": True,
    }).text
    chunks = [line[6:] for line in text.splitlines() if line.startswith("data: ")]
    assert chunks[-1] == "[DONE]"
    assert json.loads(chunks[0])["choices"][0]["delta"]["content"] == "hello from dual-lobe"


def test_clinical_mode_sends_system_message_as_patient_context(monkeypatch):
    monkeypatch.setenv("DUAL_LOBE_SERVICE_MODE", "clinical")
    seen = []
    client = _client(monkeypatch, seen)
    client.post("/v1/chat/completions", json={
        "messages": [{"role": "system", "content": "Age 70, on warfarin"}, {"role": "user", "content": "Add aspirin?"}],
    })
    assert seen[0].patient_context == "Age 70, on warfarin"
    assert seen[0].message == "Add aspirin?"


def test_api_key_is_enforced_when_set(monkeypatch):
    monkeypatch.setenv("DUAL_LOBE_SERVER_API_KEY", "secret")
    client = _client(monkeypatch, [])
    assert client.get("/v1/models").status_code == 401
    assert client.get("/v1/models", headers={"Authorization": "Bearer secret"}).status_code == 200


def test_last_message_must_be_user(monkeypatch):
    client = _client(monkeypatch, [])
    r = client.post("/v1/chat/completions", json={"messages": [{"role": "assistant", "content": "x"}]})
    assert r.status_code == 400
