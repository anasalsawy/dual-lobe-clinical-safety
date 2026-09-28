from datetime import date
from types import SimpleNamespace

import pytest

from clinical_fakes import RECORD
from dual_lobe_crewai.provider_control import ProviderSpec
from dual_lobe_crewai.runner import EgressDenied, apply_egress_filters
from dual_lobe_clinical import egress
from dual_lobe_clinical.egress import EGRESS_MONITOR, EgressMonitor
from dual_lobe_clinical.locality import LocalityError, is_local_destination, resolve_b_specs
from dual_lobe_clinical.privacy import PrivacySession, VaultDestroyed

IDX = date(2026, 9, 28)


def view_text(record=RECORD, question="What ibuprofen dose for Walter Hargrove?"):
    s = PrivacySession(index_date=IDX)
    v = s.build_view(question, record)
    return s, v, v.all_text()


def test_structured_identifiers_removed_and_age_derived():
    s, v, text = view_text()
    for raw in ["Walter", "Hargrove", "MRN-0048213", "201-3344", "14 Elm Street", "Springfield", "62704",
                "Linda", "555-201-9876", "1954-03-02"]:
        assert raw not in text
    assert "age_years: 72" in text
    # identifier fields are dropped from the view, not just tokenized
    assert "patient.mrn" not in text and "emergency_contact" not in text


def test_narrative_names_found_by_propagation_and_cues():
    _, _, text = view_text()
    assert "Mr. [NAME#" in text
    assert "daughter [NAME#" in text  # relation cue: "His daughter Priya"


def test_same_person_same_token_within_session_different_across_sessions():
    s1, v1, t1 = view_text()
    s2, v2, t2 = view_text()
    tok1 = t1.split("Mr. ")[1].split("]")[0]
    assert tok1 in v1.question  # "Walter Hargrove" in the question -> same token as "Mr. Hargrove"
    assert tok1 not in t2


def test_dates_become_relative_offsets():
    _, _, text = view_text()
    assert "[DATE T-14d#" in text and "[DATE T-8d#" in text
    assert "2026-09-14" not in text and "09/20/2026" not in text


def test_age_over_89_generalized():
    s = PrivacySession(index_date=IDX)
    v = s.build_view("Dose for a 94-year-old?", {"age": 97, "note": "Aged 91, lives alone."})
    text = v.all_text()
    assert "94" not in text and "97" not in text and "91" not in text
    assert text.count("90+") == 3


def test_common_words_are_not_redacted_by_name_parts():
    s = PrivacySession(index_date=IDX)
    v = s.build_view("q", {"name": "May Grant", "note": "Symptoms may improve; grant request pending. May Grant agrees."})
    text = v.render_facts()
    assert "Symptoms may improve; grant request pending." in text
    assert "May Grant" not in text


def test_ids_need_a_digit_so_words_survive():
    s = PrivacySession(index_date=IDX)
    text = s.pseudonymize_text("Insurance plan pending; account for fluid balance; policy # AB12345.")
    assert "Insurance plan pending; account for fluid balance" in text
    assert "AB12345" not in text


def test_rehydration_restores_exact_values():
    s, v, text = view_text()
    restored = s.rehydrate(v.render_facts())
    assert "Mr. Walter J. Hargrove" in restored or "Mr. Hargrove" in restored
    assert "2026-09-14" in restored and "walt.h@example.com" in restored


def test_vault_holds_no_plaintext_identifiers():
    s, _, _ = view_text()
    blob = repr(s.vault.__dict__).encode() + b"".join(ct for _, ct in s.vault._cipher.values())
    for raw in [b"Hargrove", b"0048213", b"walt.h", b"Springfield"]:
        assert raw not in blob


def test_destroy_is_crypto_shredding():
    s, v, _ = view_text()
    receipt = s.destroy()
    assert receipt.key_destroyed and s.vault.token_count == 0
    assert all(b == 0 for b in s.vault._enc_key) and len(s.vault._enc_key) == 0
    with pytest.raises(VaultDestroyed):
        s.rehydrate(v.question)
    assert all("Hargrove" not in (e.detail + e.fingerprint) for e in receipt.audit_log)


def test_residual_registration_propagates():
    s, v, text = view_text()
    assert "Tomasz" in text and "Sedona" in text
    s.register_residual([("Tomasz", "NAME"), ("Sedona", "LOCATION")])
    text2 = s.reapply(v).all_text()
    assert "Tomasz" not in text2 and "Sedona" not in text2
    assert s.destroy().detection_sources.get("local_b_sweep") == 2


def test_free_text_record():
    s = PrivacySession(index_date=IDX)
    v = s.build_view("q", "Ms. Okafor, DOB 04/02/1961, phone +44 20 7946 0958, seen 2026-09-01.")
    text = v.all_text()
    assert "Okafor" not in text and "7946" not in text and "1961" not in text


# -- locality -----------------------------------------------------------------

@pytest.mark.parametrize(
    "model,base,local",
    [
        ("ollama/llama3.1", None, True),
        ("hosted_vllm/m", "http://127.0.0.1:8000/v1", True),
        ("openai/m", "http://localhost:1234/v1", True),
        ("openrouter/x/y", None, False),
        ("hosted_vllm/m", "https://api.groq.com/openai/v1", False),
        ("hosted_vllm/m", "http://10.0.0.5:8000/v1", False),  # private IPs must be allowlisted explicitly
    ],
)
def test_locality_by_destination(model, base, local, monkeypatch):
    for var in ("OLLAMA_API_BASE", "OLLAMA_HOST", "DUAL_LOBE_CLINICAL_LOCAL_HOSTS"):
        monkeypatch.delenv(var, raising=False)
    assert is_local_destination(model, base) is local


def test_allowlisted_inhouse_host_and_remote_ollama(monkeypatch):
    monkeypatch.setenv("DUAL_LOBE_CLINICAL_LOCAL_HOSTS", "llm.hospital.internal")
    assert is_local_destination("hosted_vllm/m", "https://llm.hospital.internal/v1")
    monkeypatch.setenv("OLLAMA_API_BASE", "https://ollama.example.com")
    assert not is_local_destination("ollama/llama3.1", None)


def test_b_never_fails_over_to_a_remote_provider(monkeypatch):
    from clinical_fakes import configure_env
    configure_env(monkeypatch)
    specs, all_local = resolve_b_specs("require")
    assert all_local and specs and all(s.model.startswith("ollama/") for s in specs)
    configure_env(monkeypatch, b_model="openrouter/x/y")
    with pytest.raises(LocalityError):
        resolve_b_specs("require")


# -- egress monitor --------------------------------------------------------------

REMOTE = ProviderSpec(model="openrouter/x/y", max_tokens=10)
LOCAL = ProviderSpec(model="ollama/m", max_tokens=10)


def test_runner_filter_sanitizes_remote_and_passes_local(monkeypatch):
    for var in ("OLLAMA_API_BASE", "OLLAMA_HOST"):
        monkeypatch.delenv(var, raising=False)
    egress.install()
    s, _, _ = view_text()
    EGRESS_MONITOR.register(s)
    try:
        leaked = "Follow up with Walter Hargrove at walt.h@example.com"
        out = apply_egress_filters(REMOTE, leaked)
        assert "Hargrove" not in out and "walt.h" not in out
        assert apply_egress_filters(LOCAL, leaked) == leaked
    finally:
        EGRESS_MONITOR.unregister(s)
    receipt = s.destroy()
    assert receipt.outbound_sanitized_at_egress == 1 and receipt.outbound_to_local == 1


def test_no_active_session_means_no_interference():
    assert apply_egress_filters(REMOTE, "Walter Hargrove") == "Walter Hargrove"


def test_crewai_hook_sanitizes_every_message_including_tool_results():
    mon = EgressMonitor()
    s, _, _ = view_text()
    mon.register(s)
    ctx = SimpleNamespace(
        llm=SimpleNamespace(model="openrouter/x/y", base_url=None),
        messages=[
            {"role": "system", "content": "You are A."},
            {"role": "tool", "content": "memory: Mr. Hargrove, MRN-0048213"},
            {"role": "user", "content": [{"type": "text", "text": "call (555) 201-3344"}]},
        ],
    )
    assert mon.crewai_hook(ctx) is None
    flat = str(ctx.messages)
    assert "Hargrove" not in flat and "0048213" not in flat and "201-3344" not in flat
    local_ctx = SimpleNamespace(llm=SimpleNamespace(model="ollama/m", base_url=None),
                                messages=[{"role": "user", "content": "Mr. Hargrove"}])
    mon.crewai_hook(local_ctx)
    assert local_ctx.messages[0]["content"] == "Mr. Hargrove"


def test_egress_fails_closed_when_sanitizer_breaks(monkeypatch):
    mon = EgressMonitor()
    s, _, _ = view_text()
    mon.register(s)

    def broken(*a, **k):
        raise ValueError("boom")

    monkeypatch.setattr(s, "sanitize_outbound", broken)
    with pytest.raises(EgressDenied):
        mon(REMOTE, "anything")
    assert s.outbound_blocked == 1
    ctx = SimpleNamespace(llm=SimpleNamespace(model="openrouter/x/y", base_url=None),
                          messages=[{"role": "user", "content": "x"}])
    assert mon.crewai_hook(ctx) is False
