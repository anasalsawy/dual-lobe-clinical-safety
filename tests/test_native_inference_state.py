import asyncio

from dual_lobe_crewai.inference_state import NativeInferenceStateManager


def test_server_root_strips_v1():
    assert (
        NativeInferenceStateManager._server_root("http://127.0.0.1:8080/v1")
        == "http://127.0.0.1:8080"
    )


def test_prepare_assigns_separate_slots_to_a_and_b(monkeypatch):
    monkeypatch.setenv("DUAL_LOBE_NATIVE_STATE", "true")
    mgr = NativeInferenceStateManager()

    async def fake_probe(root):
        return [0, 1]

    calls = []

    def fake_request(method, url, payload=None):
        calls.append((method, url, payload))
        return {}

    monkeypatch.setattr(mgr, "_probe_slots", fake_probe)
    monkeypatch.setattr(mgr, "_request_json", fake_request)

    async def run():
        a = await mgr.prepare(
            base_url="http://127.0.0.1:8080/v1",
            state_key="clinical:A",
        )
        assert a is not None
        assert a.slot_id == 0
        assert a.extra_body == {"id_slot": 0, "cache_prompt": True}
        mgr.release(a)

        b = await mgr.prepare(
            base_url="http://127.0.0.1:8080/v1",
            state_key="clinical:B",
        )
        assert b is not None
        assert b.slot_id == 1
        assert b.extra_body == {"id_slot": 1, "cache_prompt": True}
        mgr.release(b)

    asyncio.run(run())


def test_checkpoint_saves_native_slot(monkeypatch):
    monkeypatch.setenv("DUAL_LOBE_NATIVE_STATE", "true")
    mgr = NativeInferenceStateManager()

    async def fake_probe(root):
        return [0]

    calls = []

    def fake_request(method, url, payload=None):
        calls.append((method, url, payload))
        return {}

    monkeypatch.setattr(mgr, "_probe_slots", fake_probe)
    monkeypatch.setattr(mgr, "_request_json", fake_request)

    async def run():
        state = await mgr.prepare(
            base_url="http://127.0.0.1:8080/v1",
            state_key="clinical:A",
        )
        assert state is not None
        await mgr.checkpoint(state)

    asyncio.run(run())

    assert any("action=restore" in url for _, url, _ in calls)
    assert any("action=save" in url for _, url, _ in calls)


def test_unsupported_backend_does_not_fake_native_state(monkeypatch):
    monkeypatch.setenv("DUAL_LOBE_NATIVE_STATE", "true")
    mgr = NativeInferenceStateManager()

    async def fake_probe(root):
        return None

    monkeypatch.setattr(mgr, "_probe_slots", fake_probe)

    state = asyncio.run(
        mgr.prepare(
            base_url="https://api.example.com/v1",
            state_key="clinical:A",
        )
    )
    assert state is None
