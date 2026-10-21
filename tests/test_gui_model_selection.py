"""Model selection must change physics and survive persistence and editing."""
import json
from pathlib import Path
import jax.numpy as jnp
import pytest
from difflow.gui import FlowsheetSession
from difflow.gui.model_selection import nrtl_example
from difflow import serialize, codegen


def session():
    return FlowsheetSession(path=Path(__file__).parents[1] /
                            'src/difflow/gui/examples/01_flash_drum.json')


def choose(s, mode):
    config = {"model": mode}
    if mode == 'NRTL':
        config.update(nrtl_example(['water', 'ethanol']))
    elif mode in ('PengRobinson', 'SRK'):
        config['k_ij'] = [[0, 0.075], [0.075, 0]]
    result = s.patch_unit('flash', {'equilibrium_model': config})
    assert result['ok'], result
    return s.flowsheet.units[0].operation


@pytest.mark.parametrize('mode', ['Raoult', 'NRTL', 'PengRobinson', 'SRK'])
def test_selection_roundtrip_and_parameter_edit(mode, tmp_path):
    s = session()
    choose(s, mode)
    before = s.document()['flowsheet']['units'][0]['runtime_model']
    assert before['model'] == mode
    target = tmp_path / 'selected.json'
    assert s.save(str(target))['ok']
    loaded = FlowsheetSession(path=target)
    assert loaded.document()['flowsheet']['units'][0]['runtime_model'] == before
    assert loaded.patch_unit('flash', {'params': {'species_order': ['water', 'ethanol']}})['ok']
    assert loaded.document()['flowsheet']['units'][0]['runtime_model'] == before


@pytest.mark.parametrize('mode', ['NRTL', 'PengRobinson', 'SRK'])
def test_python_export_keeps_the_selected_model(mode):
    s = session()
    choose(s, mode)
    source = codegen.to_python(s.flowsheet, include_solve=False, refs=s.bindings)
    scope = {}
    exec(source, scope)
    op = scope['fs'].units[0].operation
    if mode == 'NRTL':
        assert op.eos is None
        assert tuple(op.activity_model.species) == ('water', 'ethanol')
        assert float(op.activity_model.a[0, 1]) == pytest.approx(-0.8009)
    else:
        assert type(op.eos).__name__ == mode
        assert float(op.eos.params.k_ij[0, 1]) == pytest.approx(0.075)


def test_model_change_clears_result_and_undo_restores_it():
    s = session()
    ideal = s.solve()
    assert ideal['ok']
    choose(s, 'NRTL')
    assert s.streams is None
    real = s.solve()
    assert real['ok']
    assert real['models_used']['flash']['model'] == 'NRTL'
    assert ideal['streams']['vapor']['F_water'] != pytest.approx(real['streams']['vapor']['F_water'])
    assert s.undo()['ok']
    assert s.flowsheet.units[0].operation.activity_model is None
    assert s.redo()['ok']
    assert s.flowsheet.units[0].operation.activity_model is not None
    choose(s, 'PengRobinson')
    choose(s, 'Raoult')
    op = s.flowsheet.units[0].operation
    assert op.eos is None and op.activity_model is None and op.k_ij is None


@pytest.mark.parametrize('mode', ['PengRobinson', 'SRK'])
def test_selected_eos_can_run_the_flash(mode):
    import math
    s = session()
    choose(s, mode)
    answer = s.solve()
    assert answer['ok'], answer
    assert answer['models_used']['flash']['model'] == mode
    for species in ('water', 'ethanol'):
        values = [answer['streams'][p][f'F_{species}'] for p in ('liquid', 'vapor')]
        assert all(math.isfinite(v) for v in values)
        assert sum(values) == pytest.approx(1.0, abs=1e-6)


@pytest.mark.parametrize('config', [
    {'model': 'UNIQUAC'},
    {'model': 'NRTL', 'a': [[0, 1]], 'b': [[0, 0], [0, 0]], 'alpha': [[0, .3], [.3, 0]]},
    {'model': 'NRTL', 'a': [[0, True], [1, 0]], 'b': [[0, 0], [0, 0]], 'alpha': [[0, .3], [.3, 0]]},
    {'model': 'NRTL', 'a': [[0, 1], [1, 0]], 'b': [[0, 0], [0, 0]], 'alpha': [[0, .3], [.2, 0]]},
    {'model': 'PengRobinson', 'k_ij': [[0, float('nan')], [0, 0]]},
    {'model': 'SRK', 'k_ij': [[0, .1], [.2, 0]]},
])
def test_invalid_model_change_is_atomic(config):
    s = session()
    op = s.flowsheet.units[0].operation
    before = s._state()
    result = s.patch_unit('flash', {'equilibrium_model': config})
    assert not result['ok']
    assert s.flowsheet.units[0].operation is op
    assert s._state() == before


def test_example_parameter_order_is_explicit():
    assert nrtl_example(['water', 'ethanol'])['b'][0][1] == 246.18
    assert nrtl_example(['ethanol', 'water'])['b'][0][1] == -586.0809
    assert nrtl_example(['water', 'methanol']) is None


@pytest.mark.parametrize('order', [['ethanol', 'water'], None, 'water,ethanol'])
def test_species_reorder_does_not_reinterpret_nrtl_parameters(order):
    s = session()
    op = choose(s, 'NRTL')
    result = s.patch_unit('flash', {'params': {'species_order': order}})
    assert not result['ok']
    assert s.flowsheet.units[0].operation is op


def test_model_change_through_the_gui_http_route():
    import threading
    import urllib.request
    from difflow.gui import make_server
    from difflow.gui.server import TOKEN_HEADER
    s = session()
    server = make_server(s, port=0)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        config = {'model': 'NRTL', **nrtl_example(['water', 'ethanol'])}
        req = urllib.request.Request(
            f'http://127.0.0.1:{server.server_address[1]}/api/unit/flash',
            data=json.dumps({'equilibrium_model': config}).encode(), method='PATCH',
            headers={'Content-Type': 'application/json', TOKEN_HEADER: server.token})
        with urllib.request.urlopen(req) as reply:
            assert json.load(reply)['ok']
        assert s.document()['flowsheet']['units'][0]['runtime_model']['model'] == 'NRTL'
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)
