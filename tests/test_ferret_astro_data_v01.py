from gremlin_mcp.ferret_astro import (
    build_bestiary_handoff,
    build_fits_provenance_receipt,
    prepare_astro_source,
    prepare_library_proxy_source,
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


def test_prepare_noema_library_proxy_source():
    selector = (
        "noema://zip/sha256/"
        "fef25a4cb20380483fec5b3e84ad8a2d1465e6a53ecf6dfd9ec42ec67d82e9ef"
        "/entry/9e3d155ba6152b9c5ec5a7643ad2fdaf20da68348870ea5601204f895613cd8e"
    )
    src = prepare_library_proxy_source({
        "selector_uri": selector,
        "archive_sha256": "fef25a4cb20380483fec5b3e84ad8a2d1465e6a53ecf6dfd9ec42ec67d82e9ef",
        "entry_sha256": "61770ad10ac6eb20b85a6587da21149b5e46d69b33273ff9f5eea93ed09d44a1",
        "byte_count": 2563200,
        "file_name": "107_-26_Equ_J2000_planck_143Rel3.fits",
        "product": "Planck 143 GHz Release 3 recovered cutout",
        "kind": "CMB_FREQUENCY",
        "ra_deg": 107.576646,
        "dec_deg": -25.907579,
    })
    assert src["status"] == "PREPARED_LIBRARY_PROXY"
    assert src["live_observation_claim"] is False
    assert src["canon_allowed"] is False

    prov = build_fits_provenance_receipt(
        src,
        file_name=src["file_name"],
        header={"BUNIT": "Kcmb", "NAXIS1": 800, "NAXIS2": 800},
    )
    assert prov["sha256"] == src["entry_sha256"]
    assert prov["byte_count"] == 2563200
    assert prov["source_host"] == "NOEMA_LIBRARY_ZIP_MEMBER"
