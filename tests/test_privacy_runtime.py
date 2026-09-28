import json

from dual_lobe_clinical.privacy import PrivacyGuard


def test_a_side_can_receive_tokenized_context_while_local_b_can_keep_raw_data():
    guard = PrivacyGuard(audit_key=b"test")
    vault = guard.new_vault()
    query = "Send Jane Doe's result"
    context = json.dumps({"name": "Jane Doe", "diagnosis": "asthma"})
    safe_query, safe_context, receipt = guard.prepare(
        query=query,
        patient_context=context,
        vault=vault,
    )
    assert "Jane Doe" not in safe_query
    assert "Jane Doe" not in safe_context
    assert "<PHI:" in safe_query or "<PHI:" in safe_context
    assert receipt.raw_phi_forwarded is False
    # The raw values remain available to the local runtime/B through the original inputs.
    assert "Jane Doe" in query and "Jane Doe" in context
    vault.destroy_key()


def test_b_output_is_sanitized_before_remote_a_review():
    guard = PrivacyGuard(audit_key=b"test")
    vault = guard.new_vault()
    _, _, _ = guard.prepare(
        query="q",
        patient_context=json.dumps({"name": "Jane Doe"}),
        vault=vault,
    )
    safe, _ = guard.sanitize_trace("Tool returned Jane Doe", vault=vault)
    assert "Jane Doe" not in safe
    assert "<PHI:" in safe
    vault.destroy_key()
