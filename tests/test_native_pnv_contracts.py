from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
NATIVE = ROOT / "native"
FILES = sorted(NATIVE.glob("*.pnv"))
ALLOWED = {"SOURCE","IDENTITY","DIFFERENCE","CONDITION","ORDER","TRANSFORM","COMPOSITION","RETURN"}
REQUIRED_NATIVE = {
    "BELZEBUB_TOOL_V0_4.pnv",
    "GREMLIN_KAKU_RADICAL_WRITER_V0_1.pnv",
    "GREMLIN_NATURAL_QUEUE_TAU_V0_4.pnv",
    "GREMLIN_PERSISTENT_MEMORY_V0_4.pnv",
    "GREMLIN_PHASENAV_PROTOTYPE_PIPELINE_V0_1.pnv",
    "GREMLIN_QHTRI_M0_M11_ISOMORPHISM_SCAN_V0_1.pnv",
    "GREMLIN_QHTRI_TORUS_CHARACTER_SCAN_V0_2.pnv",
    "GREMLIN_SYSTEM_V0_4.pnv",
    "GREMLIN_TRIPLE_PULSE_BOOT_V0_5.pnv",
    "OCTOPUS_TOOL_V0_4.pnv",
}


def parse_ops(text):
    ops=[]
    for line in text.splitlines():
        if line.startswith("OP "):
            parts=line.split()
            assert len(parts) >= 4, line
            ops.append(parts[2])
    return ops


def test_required_native_units_present():
    assert REQUIRED_NATIVE <= {p.name for p in FILES}


def test_native_header_and_epistemic():
    for p in FILES:
        lines=p.read_text().splitlines()
        assert lines[0] == "PNV 1"
        assert lines[1] == "EPISTEMIC CHYBA"


def test_existing_opcodes_only():
    for p in FILES:
        text=p.read_text()
        assert set(parse_ops(text)) <= ALLOWED
        assert "# NEW_PNV_OPCODES 0" in text


def test_persistent_memory_heads():
    text=(NATIVE/"GREMLIN_PERSISTENT_MEMORY_V0_4.pnv").read_text()
    assert "GREMLIN_PROTOCOL OBJECT->RECEIPT->SUPER_CURRENT" in text
    assert "TOOL_PROTOCOL OBJECT->RECEIPT->CURRENT" in text
    assert "OCTOPUS_CURRENT_AUTHORITATIVE TRUE" in text
    assert "BELZEBUB_CURRENT_AUTHORITATIVE TRUE" in text
    assert "LAST_WRITER_WINS FALSE" in text


def test_distinct_tool_current_paths():
    root=(NATIVE/"GREMLIN_SYSTEM_V0_4.pnv").read_text()
    octo="/dev/shm/ciel_noema/gremlin/tools/octopus/meta/CURRENT.json"
    bel="/dev/shm/ciel_noema/gremlin/tools/belzebub/meta/CURRENT.json"
    assert octo in root and bel in root and octo != bel
    assert "/dev/shm/ciel_noema/gremlin/meta/SUPER_CURRENT.json" in root


def test_tools_have_local_write_authority():
    for name in ["OCTOPUS_TOOL_V0_4.pnv","BELZEBUB_TOOL_V0_4.pnv"]:
        text=(NATIVE/name).read_text()
        assert "# WRITE_AUTHORITY OWN_NAMESPACE" in text
        assert "# AUTHORITY_POINTER CURRENT" in text
        assert "# STORAGE_PROTOCOL OBJECT->RECEIPT->CURRENT" in text


def test_belzebub_defensive_boundary():
    text=(NATIVE/"BELZEBUB_TOOL_V0_4.pnv").read_text()
    assert "# QUARANTINE_EXECUTION FALSE" in text
    assert "# SELF_PROPAGATION FALSE" in text
    assert "# IMMUNITY_PROMOTION REQUIRES_VERIFIED_TEST_RECEIPT" in text


def test_natural_queue_tau_contract():
    text=(NATIVE/"GREMLIN_NATURAL_QUEUE_TAU_V0_4.pnv").read_text()
    assert "# NATURAL_CONTINUATION ORDER->TRANSFORM->COMPOSITION" in text
    assert "# TAU_IS_PRIORITY FALSE" in text
    assert "# MASS_BINDING_REQUIRED TRUE" in text
    assert "# TICK_REQUIRED FALSE" in text


def test_torus_character_scan_contract():
    text=(NATIVE/"GREMLIN_QHTRI_TORUS_CHARACTER_SCAN_V0_2.pnv").read_text()
    assert "# CHARACTER_KERNEL KCHI_TORUS_CHARACTER_FIELD" in text
    assert "# CHARACTER_LATTICE Z36" in text
    assert "# EXECUTION_KERNEL_FAMILIES 3" in text
    assert "# REDUCER_PRIMITIVE PHASE_CENTROID" in text
    assert "# NO_GCD_NORMALIZATION TRUE" in text
    assert "# ARBITRARY_MULTI_MODE_SINGLE_CHARACTER_COLLAPSE FALSE" in text
    assert "# LIVE_NOEMA_WITNESS TRUE" in text
    assert "# LIVE_GREMLIN_PRODUCER_WITNESS FALSE" in text


def test_phasenav_prototype_pipeline_contract():
    text=(NATIVE/"GREMLIN_PHASENAV_PROTOTYPE_PIPELINE_V0_1.pnv").read_text()
    assert "# PIPELINE SURVIVED_AUDIT->PHASENAV_IR_CANDIDATE->UNTRUSTED_PROTOTYPE->VALIDATED_PROTOTYPE" in text
    assert "# VALIDATED_SCOPE REFERENCE_CONFORMANCE_ONLY" in text
    assert "# PHASENAV_SPACE T36" in text
    assert "# PHASENAV_DUAL_LATTICE Z36" in text
    assert "# EXPLICIT_RELATION_COMPILATION TRUE" in text
    assert "# TEXT_TO_EXECUTION_INFERENCE FALSE" in text
    assert "# SANDBOX_REQUIRED TRUE" in text
    assert "# PRODUCTION_RUNTIME_WRITE FALSE" in text
    assert "# EXECUTION_AUTHORITY FALSE" in text
    assert "# CANON_ALLOWED FALSE" in text
    assert "# BELZEBUB_SURVIVAL_REQUIRED TRUE" in text
    assert "# PYTHON_ROLE REFERENCE_AND_TEST_HARNESS_ONLY" in text


def test_kaku_radical_writer_contract():
    text=(NATIVE/"GREMLIN_KAKU_RADICAL_WRITER_V0_1.pnv").read_text()
    assert "# KAKU_SCHEMA GREMLIN_KAKU_SCALAR_PACKET_V0_1" in text
    assert "# KAKU_RECORD_SCHEMA GREMLIN_KAKU_PERSISTENCE_RECORD_V0_1" in text
    assert "# RADICAL_SCHEMA GREMLIN_RADICAL_SCALAR_ADMISSION_V0_1" in text
    assert "# RADICAL_RECORD_SCHEMA GREMLIN_RADICAL_PERSISTENCE_RECORD_V0_1" in text
    assert "# EXACT_ORDERED_KAKU_LINEAGE TRUE" in text
    assert "# KAKU_CONTENT_ADDRESSED TRUE" in text
    assert "# RADICAL_CONTENT_ADDRESSED TRUE" in text
    assert "# STORE_POLICY IMMUTABLE_IDEMPOTENT" in text
    assert "# PATH_COLLISION DIFFERENT_BYTES_FAIL_CLOSED" in text
    assert "# PRE_VECTOR_STATUS_PRESERVED TRUE" in text
    assert "# HARD_GATE_STATUS_PRESERVED TRUE" in text
    assert "# EXECUTION_AUTHORITY FALSE" in text
    assert "# CANON_ALLOWED FALSE" in text
    assert "# PRODUCTION_RUNTIME_WRITE FALSE" in text
    assert "# PHASENAV_REALIZATION_REQUIRED_LATER TRUE" in text


def test_no_python_authority_claim_in_spec():
    text=(ROOT/"spec/GREMLIN_RUNTIME_HIERARCHY_V0_4.md").read_text()
    assert "Python code is reference/test harness only" in text
