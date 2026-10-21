# Active flash model in the local editor

The selected TP Flash now shows its live equilibrium model, phase
assumptions, property package, species order, numerical method and
interaction parameters. Its equations follow the active branch rather
than the catalog's static Raoult-law example.

`Models used for this solve` in the results panel records the model and
parameter values captured immediately before that solve. It is a detached
snapshot, not a reference to the operation currently on the canvas.

The first version supports the built-in `Flash` and `EOSFlash` classes.
It follows the solver's precedence: EOS, then NRTL, then the supplied
K-value package. Unrecognized property packages are not labelled Raoult.
Overrides of these classes are left undescribed rather than guessed.
Console changes to the supported models now invalidate the displayed
solution and refresh the inspector, even when optional constructor
arguments are absent from the serialized flowsheet.

This change does not add model selection, automatic parameter sourcing or
serialization of optional models. NRTL attached from the console can still
be lost on reopening a file or rebuilding the unit; the live label reports
what remains attached. NRTL parameters copied from the project's tests
are not independently validated experimental data. The existing activity
flash runs 30 composition updates, and its balance verdict is not an
independent check of phase-equilibrium convergence.

The GUI static bundle is included, so using the patch does not require
Node.js. After updating, restart `python -m difflow.gui` and reload the
browser page. Backend tests: `python -m pytest tests/test_gui_active_model.py -q`.
