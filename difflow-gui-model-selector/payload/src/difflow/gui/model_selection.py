"""Validated, atomic model changes for the built-in TP Flash editor."""
import math


def matrix(value, n: int, name: str, symmetric: bool = False):
    """Check a finite n-by-n matrix with zero diagonal before building JAX data."""
    if not isinstance(value, list) or len(value) != n:
        raise ValueError(f"{name} must be a {n} x {n} JSON matrix")
    rows = []
    for row in value:
        if not isinstance(row, list) or len(row) != n:
            raise ValueError(f"{name} must be a {n} x {n} JSON matrix")
        if any(isinstance(x, bool) or not isinstance(x, (float, int))
               or not math.isfinite(x) for x in row):
            raise ValueError(f"{name} must contain finite numbers")
        rows.append([float(x) for x in row])
    if any(abs(rows[i][i]) > 1e-12 for i in range(n)):
        raise ValueError(f"{name} diagonal must be zero")
    if symmetric and any(abs(rows[i][j] - rows[j][i]) > 1e-12
                         for i in range(n) for j in range(n)):
        raise ValueError(f"{name} must be symmetric")
    return rows


def nrtl_example(species):
    """The repository test's water/ethanol parameters, reordered explicitly."""
    if len(species) != 2 or set(species) != {"water", "ethanol"}:
        return None
    # tests/test_flash_azeotrope.py uses ethanol first.
    indices = [("ethanol", "water").index(s) for s in species]
    data = {"a": [[0.0, 3.4578], [-0.8009, 0.0]],
            "b": [[0.0, -586.0809], [246.18, 0.0]],
            "alpha": [[0.0, 0.3], [0.3, 0.0]]}
    return {key: [[m[i][j] for j in indices] for i in indices]
            for key, m in data.items()}


def select_model(operation, config: dict):
    """Build a replacement without mutating the old operation on any failure."""
    import jax.numpy as jnp
    from difflow import IdealThermo, PengRobinson, SRK, get_critical_props
    from difflow.units.flash import Flash
    from difflow.units.lle import NRTLParams

    if type(operation) is not Flash or type(operation.thermo) is not IdealThermo:
        raise ValueError("Model selection currently supports built-in Flash with IdealThermo data")
    if not isinstance(config, dict):
        raise ValueError("equilibrium_model must be an object")
    mode = config.get("model")
    allowed = {"Raoult": {"model"}, "NRTL": {"model", "a", "b", "alpha"},
               "PengRobinson": {"model", "k_ij"}, "SRK": {"model", "k_ij"}}
    if mode not in allowed:
        raise ValueError("Choose Raoult, NRTL, PengRobinson or SRK")
    if set(config) - allowed[mode]:
        raise ValueError("Unexpected parameters for the selected model")
    species = list(operation.params.species_order)
    if species != operation.thermo.species_order:
        raise ValueError("Property-package order does not match the flash species order")
    n = len(species)
    activity, eos, kij = None, None, None
    if mode == "NRTL":
        mats = {key: matrix(config.get(key), n, key, symmetric=key == "alpha")
                for key in ("a", "b", "alpha")}
        if any(not 0 <= x <= 1 for row in mats["alpha"] for x in row):
            raise ValueError("alpha entries must be between zero and one")
        activity = NRTLParams(species=tuple(species),
                              **{key: jnp.asarray(m) for key, m in mats.items()})
    elif mode in ("PengRobinson", "SRK"):
        kij = jnp.asarray(matrix(config.get("k_ij"), n, "k_ij", symmetric=True))
        props = {s: get_critical_props(s) for s in species}
        eos = {"PengRobinson": PengRobinson, "SRK": SRK}[mode](props, k_ij=kij)
    return Flash(operation.params, operation.thermo, eos=eos,
                 k_ij=kij, activity_model=activity)
