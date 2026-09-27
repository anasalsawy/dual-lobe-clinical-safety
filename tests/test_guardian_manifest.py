import hashlib
import pytest
from dual_lobe_clinical.guardian import GuardianModelManifest


def make_manifest(artifact, digest):
    return GuardianModelManifest(
        manifest_version="1",model_id="guardian-v1",base_model="base",
        fine_tune_profile="clinical-v1",artifact_path=str(artifact),
        artifact_sha256=digest,training_data_version="train-v1",
        intended_roles=("clinical_context_broadening","adversarial_claim_audit","privacy_oversight"),
    )


def test_guardian_manifest_verifies_known_artifact(tmp_path):
    artifact=tmp_path/"adapter.bin"
    artifact.write_bytes(b"known guardian")
    make_manifest(artifact,hashlib.sha256(artifact.read_bytes()).hexdigest()).assert_primary_ready()


def test_guardian_manifest_rejects_wrong_hash(tmp_path):
    artifact=tmp_path/"adapter.bin"
    artifact.write_bytes(b"known guardian")
    with pytest.raises(ValueError,match="hash/path"):
        make_manifest(artifact,"0"*64).assert_primary_ready()
