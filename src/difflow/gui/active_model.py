"""Describe the live TP-flash branch; never infer it from catalog prose.

The returned values are detached JSON data, so a solve response retains the
model it used even if the live operation is subsequently edited.
"""


def flash_model(operation):
    """Return active-model metadata for supported TP flashes, or ``None``."""
    from difflow.thermo import IdealThermo
    from difflow.units.flash import Flash, EOSFlash
    from copy import deepcopy

    def snapshot(value):
        return value.tolist() if hasattr(value, "tolist") else deepcopy(value)

    # A subclass may override __call__; do not promise its parent's physics.
    if type(operation) not in (Flash, EOSFlash):
        return None
    eos = getattr(operation, "eos", None)
    activity = getattr(operation, "activity_model", None)
    thermo = getattr(operation, "thermo", None)
    out = {
        "calculation": "TP flash",
        "species": list(operation.params.species_order),
        "property_package": type(thermo).__name__ if thermo is not None else "not used",
        "parameters": {},
        "selectable": type(operation) is Flash and type(thermo) is IdealThermo,
    }
    from difflow.gui.model_selection import nrtl_example
    out["nrtl_example"] = nrtl_example(out["species"])
    rr = r"\sum_i \frac{z_i(K_i-1)}{1+\beta(K_i-1)}=0"
    # Match Flash.__call__ precedence: an EOS overrides an activity model.
    if eos is not None:
        out.update(
            model=type(eos).__name__, liquid="EOS fugacity", vapor="EOS fugacity",
            method="EOS TP flash with fugacity-based K-values.",
            equations=[rr, r"K_i=\phi_i^L/\phi_i^V"],
            assumptions=["Vapor-liquid equilibrium at specified T and P; supplied EOS."],
        )
        kij = getattr(operation, "k_ij", None)
        if kij is None:
            kij = getattr(eos.params, "k_ij", None)
        out["parameters"]["k_ij"] = snapshot(kij)
        if activity is not None:
            out["note"] = "An activity model is attached but is inactive: EOS takes precedence."
    elif activity is not None:
        out.update(
            model="NRTL", liquid="NRTL activity coefficients", vapor="Ideal gas",
            method="30 liquid-composition updates; Rachford-Rice solved with optimistix Newton at each update.",
            equations=[rr, r"K_i=\gamma_i(x,T)P_i^{sat}(T)/P", r"\tau_{ij}=a_{ij}+b_{ij}/T"],
            assumptions=["Modified Raoult law; ideal vapor, no Poynting correction.",
                         "Fixed composition-iteration count; no separate equilibrium-convergence verdict."],
        )
        out["parameters"] = {
            "species": list(activity.species),
            **{key: snapshot(getattr(activity, key)) for key in ("a", "b", "alpha")},
            "tau_convention": "a_ij + b_ij/T (T in K)",
        }
    else:
        ideal = type(thermo) is IdealThermo
        out.update(
            model="Raoult" if ideal else "Supplied K-value package",
            liquid="Ideal solution" if ideal else "Defined by property package",
            vapor="Ideal gas" if ideal else "Defined by property package",
            method="Rachford-Rice solved with optimistix Newton; phase-boundary smoothing.",
            equations=[rr, r"K_i=P_i^{sat}(T)/P"] if ideal else [rr],
            assumptions=["Ideal liquid and vapor; Antoine saturation pressures."] if ideal else [],
        )
    return out


def flowsheet_models(flowsheet):
    """Read live supported units, keyed by unit name."""
    models = {}
    for unit in flowsheet.units:
        model = flash_model(unit.operation)
        if model is not None:
            models[unit.name] = model
    return models
