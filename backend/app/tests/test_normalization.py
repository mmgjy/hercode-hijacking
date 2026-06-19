"""Normalization and synonym mapping."""
from app.models import RawSignal
from app.services.normalization_service import Normalizer


def _raw(**kw):
    base = dict(features=[], materials=[])
    base.update(kw)
    return RawSignal(**base)


def test_product_type_synonym_and_plural():
    n = Normalizer()
    ns = n.normalize(_raw(product_type="Trail Pants"))
    assert ns.normalized_product_type == "hiking trousers"


def test_feature_synonyms_map_to_canonical():
    n = Normalizer()
    for raw_feature in ["tick protection", "bug protection", "Zeckenschutz"]:
        ns = n.normalize(_raw(raw_title=f"Hiking trousers {raw_feature}"))
        assert "insect-protection" in ns.normalized_features


def test_upf_variants():
    n = Normalizer()
    ns = n.normalize(_raw(raw_title="Sun Hoodie UPF 50 sun protection"))
    assert "UPF sun protection" in ns.normalized_features
    assert ns.normalized_product_type == "hooded shirt"


def test_material_synonym():
    n = Normalizer()
    ns = n.normalize(_raw(materials=["merino"]))
    assert "merino wool" in ns.normalized_materials


def test_keeps_unmapped_value_cleaned():
    n = Normalizer()
    ns = n.normalize(_raw(product_type="Fancy Gizmo"))
    assert ns.normalized_product_type == "fancy gizmo"  # cleaned but unmapped


def test_normalization_records_terms_and_version():
    n = Normalizer()
    ns = n.normalize(_raw(product_type="trail pants", raw_title="tick protection"))
    assert ns.normalization_version
    assert ns.normalization_terms  # which synonyms matched
