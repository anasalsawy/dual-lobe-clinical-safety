import json

import pytest

from dual_lobe_clinical.privacy import (
    EphemeralClinicalMemory,
    EphemeralTokenVault,
    PrivacyAssurance,
    PrivacyDecision,
    PrivacyGuard,
    ProviderPrivacyPolicy,
)


def guard(**kwargs):
    return PrivacyGuard(
        ProviderPrivacyPolicy(**kwargs),
        audit_key=b"test-key",
    )


def test_structured_identifiers_become_random_opaque_tokens_and_can_rehydrate_locally():
    g = guard(provider_name="remote")
    vault = g.new_vault()
    context = json.dumps({
        "name": "Jane Doe",
        "mrn": "ABC123",
        "diagnosis": "asthma",
        "medications": ["albuterol"],
    })
    q, c, receipt = g.prepare(query="What should be considered?", patient_context=context, vault=vault)
    assert "Jane Doe" not in c
    assert "ABC123" not in c
    assert "<PHI:NAME:" in c
    assert "<PHI:MRN:" in c
    assert "asthma" in c
    assert "albuterol" in c
    assert receipt.decision is PrivacyDecision.SANITIZE
    assert receipt.raw_phi_forwarded is False
    assert receipt.persisted_raw_locally is False
    rehydrated = vault.rehydrate_text(c)
    assert "Jane Doe" in rehydrated
    assert "ABC123" in rehydrated


def test_token_vault_encrypts_mapping_and_does_not_expose_raw_in_snapshot():
    vault = EphemeralTokenVault()
    token = vault.tokenize("Jane Doe", label="name")
    snapshot = vault.encrypted_snapshot()
    assert token in snapshot
    assert "Jane Doe" not in json.dumps(snapshot)
    assert snapshot[token]["ciphertext_sha256"]


def test_key_destruction_prevents_rehydration():
    vault = EphemeralTokenVault()
    token = vault.tokenize("Jane Doe", label="name")
    vault.destroy_key()
    assert vault.destroyed is True
    with pytest.raises(RuntimeError):
        vault.resolve(token)


def test_same_identifier_within_run_maps_to_same_token():
    vault = EphemeralTokenVault()
    a = vault.tokenize("Jane Doe", label="name")
    b = vault.tokenize("Jane Doe", label="name")
    assert a == b


def test_same_identifier_across_runs_gets_different_token():
    a = EphemeralTokenVault().tokenize("Jane Doe", label="name")
    b = EphemeralTokenVault().tokenize("Jane Doe", label="name")
    assert a != b


def test_free_text_email_and_phone_are_tokenized():
    g = guard(provider_name="remote")
    vault = g.new_vault()
    q, c, receipt = g.prepare(
        query="Call jane@example.com or +1 713 555 1212",
        patient_context="clinical detail",
        vault=vault,
    )
    assert "jane@example.com" not in q
    assert "713 555 1212" not in q
    assert "<PHI:EMAIL:" in q
    assert "<PHI:PHONE:" in q
    assert set(receipt.direct_identifier_types) >= {"email", "phone"}


def test_remote_provider_without_attestation_is_not_claimed_safe():
    g = guard(provider_name="remote")
    vault = g.new_vault()
    _, _, receipt = g.prepare(query="q", patient_context="ctx", vault=vault)
    assert receipt.assurance is PrivacyAssurance.UNVERIFIED_REMOTE
    assert receipt.provider_zero_retention_attested is False
    assert any("not independently verified" in x for x in receipt.limitations)


def test_attested_provider_gets_distinct_assurance_state():
    g = guard(
        provider_name="attested",
        no_training_attested=True,
        zero_retention_attested=True,
        business_associate_or_equivalent=True,
    )
    vault = g.new_vault()
    _, _, receipt = g.prepare(query="q", patient_context="ctx", vault=vault)
    assert receipt.assurance is PrivacyAssurance.PROVIDER_ATTESTED


def test_trace_sanitization_uses_same_local_vault():
    g = guard(provider_name="remote")
    vault = g.new_vault()
    trace, kinds = g.sanitize_trace("tool output email jane@example.com", vault=vault)
    assert "jane@example.com" not in trace
    assert "<PHI:EMAIL:" in trace
    assert "email" in kinds


def test_ephemeral_clinical_memory_never_returns_or_records_patient_data():
    m = EphemeralClinicalMemory()
    m.record("Jane Doe")
    m.record_split_experience("patient information")
    assert m.auto_slice("Jane") == ""
    assert m.search("Jane") == []
    assert m.split_experience_slice("Jane") == ""
