Follow-up fix for the already installed GUI model patch on commit 086c56e.
Stop the GUI, then run from the repository root:
.venv\Scripts\python.exe PATH\apply_gui_model_fix2.py --repo .
Restart the GUI and reload the browser with Ctrl+F5.
The active-model card was incorrectly placed in the pending-unit branch.
This fix moves it to the built-unit branch. 224 frontend tests passed, including a render regression that fails on the previous patch.
