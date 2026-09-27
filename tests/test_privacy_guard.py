import json

from dual_lobe_clinical.privacy import (
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


def test_structured_direct_identifiers_are_removed_before_inference():
    g = guard(provider_name="remote")
    context = json.dumps({
        "name": "Jane Doe",
        "mrn": "ABC123",
        "diagnosis": "asthma",
        "medications": ["albuterol"],
    })
    q, c, receipt = g.prepare(query="What should be considered?", patient_context=context)
    assert "Jane Doe" not in c
    assert "ABC123" not in c
    assert "asthma" in c
    assert "albuterol" in c
    assert receipt.decision is PrivacyDecision.SANITIZE
    assert "name" in receipt.direct_identifier_types
    assert "mrn" in receipt.direct_identifier_types
    assert receipt.raw_phi_forwarded is False
    assert receipt.persisted_raw_locally is False


def test_free_text_email_and_phone_are_removed():
    g = guard(provider_name="remote")
    q, c, receipt = g.prepare(
        query="Call jane@example.com or +1 713 555 1212",
        patient_context="clinical detail",
    )
    assert "jane@example.com" not in q
    assert "713 555 1212" not in q
    assert set(receipt.direct_identifier_types) >= {"email", "phone"}


def test_remote_provider_without_attestation_is_not_claimed_safe():
    g = guard(provider_name="remote")
    _, _, receipt = g.prepare(query="q", patient_context="ctx")
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
    _, _, receipt = g.prepare(query="q", patient_context="ctx")
    assert receipt.assurance is PrivacyAssurance.PROVIDER_ATTESTED


def test_fingerprint_is_stable_without_exposing_content():
    g = guard(provider_name="remote")
    _, _, a = g.prepare(query="q", patient_context="same")
    _, _, b = g.prepare(query="q", patient_context="same")
    assert a.sanitized_context_fingerprint == b.sanitized_context_fingerprint
    assert "same" not in a.sanitized_context_fingerprint


def test_trace_is_sanitized_before_final_b_visibility():
    g = guard(provider_name="remote")
    trace, kinds = g.sanitize_trace("tool output email jane@example.com")
    assert "jane@example.com" not in trace
    assert "email" in kinds
