"""Regression checks for live model labels and immutable solve provenance."""
import json
from pathlib import Path

import jax.numpy as jnp
import pytest

from difflow import Flash, FlashParams, IdealThermo, get_species_data
from difflow.gui import FlowsheetSession
from difflow.gui.active_model import flash_model
from difflow.units.lle import NRTLParams


def nrtl():
    return NRTLParams(
        species=("water", "ethanol"),
        a=jnp.array([[0.0, -0.8009], [3.4578, 0.0]]),
        b=jnp.array([[0.0, 246.18], [-586.0809, 0.0]]),
        alpha=jnp.array([[0.0, 0.3], [0.3, 0.0]]),
    )


def session():
    path = Path(__file__).parents[1] / "src/difflow/gui/examples/01_flash_drum.json"
    return FlowsheetSession(path=path)


def test_console_change_is_detected_and_live_equations_follow_it():
    s = session()
    assert s.document()["flowsheet"]["units"][0]["runtime_model"]["model"] == "Raoult"
    s.bindings["nrtl_test"] = nrtl()
    result = s.console_run("fs.units[0].operation.activity_model = nrtl_test")
    assert result["error"] is None
    assert result["changed"] is True
    model = s.document()["flowsheet"]["units"][0]["runtime_model"]
    assert model["model"] == "NRTL"
    assert any("gamma" in eq for eq in model["equations"])
    assert model["parameters"]["species"] == ["water", "ethanol"]
    assert s.console_run("1 + 1")["changed"] is False


def test_solve_records_model_and_parameters_without_live_references():
    s = session()
    op = s.flowsheet.units[0].operation
    op.activity_model = nrtl()
    answer = s.solve()
    assert answer["ok"], answer
    used = answer["models_used"]["flash"]
    op.activity_model = None
    assert used["model"] == "NRTL"
    assert used["parameters"]["a"][0][1] == pytest.approx(-0.8009)
    assert s.document()["flowsheet"]["units"][0]["runtime_model"]["model"] == "Raoult"
    json.dumps(answer, allow_nan=False)


def test_eos_wins_over_attached_nrtl():
    from difflow import PengRobinson, get_critical_props
    s = session()
    op = s.flowsheet.units[0].operation
    op.activity_model = nrtl()
    op.eos = PengRobinson({n: get_critical_props(n) for n in ("water", "ethanol")})
    model = flash_model(op)
    assert model["model"] == "PengRobinson"
    assert "inactive" in model["note"]
    assert not any("gamma" in eq for eq in model["equations"])


def test_instances_of_same_class_keep_separate_labels():
    s = session()
    ideal = s.flowsheet.units[0].operation
    nonideal = Flash(ideal.params, ideal.thermo, activity_model=nrtl())
    assert flash_model(ideal)["model"] == "Raoult"
    assert flash_model(nonideal)["model"] == "NRTL"


def test_custom_package_is_not_labelled_raoult():
    op = Flash(FlashParams(["water", "ethanol"]), object())
    assert flash_model(op)["model"] == "Supplied K-value package"
