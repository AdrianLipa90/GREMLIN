from gremlin_mcp.ferret_astro import (
    build_bestiary_handoff,
    build_fits_provenance_receipt,
    prepare_astro_source,
)


def test_prepare_official_planck_source_and_handoff():
    src = prepare_astro_source({
        "source_url": "https://irsa.ipac.caltech.edu/data/Planck/release_3/all-sky-maps/previews/HFI_SkyMap_143_2048_R3.01_full/index.html",
        "product": "Planck PR3 143 GHz",
        "kind": "CMB_FREQUENCY",
        "ra_deg": 107.576646,
        "dec_deg": -25.907579,
        "query": {"frequency_ghz": 143},
        "expected_file_name": "HFI_SkyMap_143_2048_R3.01_full.fits",
    })
    assert src["status"] == "PREPARED_READ_ONLY"
    assert src["external_mutation_allowed"] is False

    prov = build_fits_provenance_receipt(
        src,
        file_name="HFI_SkyMap_143_2048_R3.01_full.fits",
        header={"PIXTYPE": "HEALPIX", "NSIDE": 2048, "FREQ": "143"},
    )
    handoff = build_bestiary_handoff([prov], task_id="PBH-CMB-PHASE-V01")
    assert handoff["status"] == "READY_FOR_BESTIARY"
    assert handoff["handoff_order"][1:5] == ["BAT", "HOUND", "OWL", "SPIDER"]
    assert handoff["ferret_worker_fanout"] is False


def test_reject_nonofficial_source():
    try:
        prepare_astro_source({
            "source_url": "https://example.com/map.fits",
            "product": "unknown",
            "kind": "CMB_COMPONENT",
            "ra_deg": 1.0,
            "dec_deg": 2.0,
        })
    except ValueError as exc:
        assert "not allowlisted" in str(exc)
    else:
        raise AssertionError("unofficial source must fail closed")
