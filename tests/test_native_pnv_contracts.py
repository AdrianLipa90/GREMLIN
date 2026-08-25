from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
NATIVE = ROOT / "native"
FILES = sorted(NATIVE.glob("*.pnv"))
ALLOWED = {"SOURCE","IDENTITY","DIFFERENCE","CONDITION","ORDER","TRANSFORM","COMPOSITION","RETURN"}


def parse_ops(text):
    ops=[]
    for line in text.splitlines():
        if line.startswith("OP "):
            parts=line.split()
            assert len(parts) >= 4, line
            ops.append(parts[2])
    return ops


def test_five_native_units_present():
    assert len(FILES) == 5


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


def test_no_python_authority_claim_in_spec():
    text=(ROOT/"spec/GREMLIN_RUNTIME_HIERARCHY_V0_4.md").read_text()
    assert "Python code is reference/test harness only" in text
