# VAC Evaluation Toolkit (LLM + RPA) — macOS Edition

This toolkit lets you produce *real* evaluation numbers on **macOS** using PyAutoGUI + an LLM planner.

## 1) macOS prerequisites
- macOS 12+ recommended, Python 3.10+
- **Grant Accessibility permissions**: System Settings → Privacy & Security → Accessibility → enable for your Terminal (Terminal/iTerm2) and Python.
- Install packages:
  ```bash
  pip install pyautogui pillow opencv-python openai python-docx pandas matplotlib jsonschema
  ```
- Optional For browser automation (Selenium):
  ```bash
  pip install selenium
  ```
- Set your OpenAI key in the same shell:
  ```bash
  export OPENAI_API_KEY="sk-..."
  ```

## 2) Files
- `runner_macos.py` — Runs test cases, calls the LLM to produce a JSON plan, executes with PyAutoGUI, logs `eval_runs.csv`.
- `analyze_results.py` — Reads `eval_runs.csv`, computes metrics, outputs plots and `Results_Report.docx`.
- `schema.json` — JSON schema for plan validation.
- `prompts/planner_system.txt` — System prompt for the planner LLM.

## 3) Run experiments
Dry-run first (no clicks):
```bash
python runner_macos.py --runs 1 --par_runs 1 --include TC1 TC2 --dry-run
```
Real runs (moves mouse/types):
```bash
python runner_macos.py --runs 3 --par_runs 2 --include TC1 TC2
```

## 4) Analyze & create report
```bash
python analyze_results.py
```
This generates `Results_Report.docx` + PNG charts.

## 5) Notes
- macOS uses `command` instead of `ctrl` for common shortcuts. The runner maps common hotkeys accordingly.
- Keep your machine idle during runs. Stop quickly by moving your mouse to a screen corner.
