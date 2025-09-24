import os, time, json, csv, argparse, random, platform, re, subprocess, textwrap
import pyautogui

from pathlib import Path
from datetime import datetime
from jsonschema import validate, ValidationError
from openai import OpenAI

pyautogui.FAILSAFE = True
IS_MAC = platform.system().lower() == "darwin"

HK_SAVE = ("command", "s")
HK_OPEN = ("command", "o")
HK_NEW  = ("command", "n")
HK_COPY = ("command", "c")
HK_PASTE= ("command", "v")
HK_SELALL=("command", "a")

BASE_DIR = Path(__file__).resolve().parent
OUT_CSV = BASE_DIR / "eval_runs.csv"
SCHEMA_PATH = BASE_DIR / "schema.json"
PLANNER_SYSTEM = BASE_DIR / "prompts" / "planner_system.txt"

TEST_CASES = {
    "TC1": {
        "instruction": "Create a new text document named 'informe semanal' and save it to the 'Documents' folder.",
        "paraphrases": [
            "Open a blank text, name it 'informe semanal' and store it under Documents.",
            "Make a text file called 'informe semanal' and save it into Documents."
        ],
        "baseline_interactions": 18,
        "app_context": "macOS, TextEdit"
    },
    "TC2": {
        "instruction": "Open https://example.com, copy the page title, paste it into a new text file, and save as 'notas.txt' in Documents.",
        "paraphrases": [
            "Go to example.com, take the page title, put it into a new text file, and save it as notas.txt in Documents.",
            "Open example.com, grab the title, paste in a new text file and store it as notas.txt under Documents."
        ],
        "baseline_interactions": 24,
        "app_context": "macOS, Safari + TextEdit"
    },
    "TC3": {
        "instruction": "In Documents, rename 'notas.txt' to 'resumen.txt' and move it to Desktop.",
        "paraphrases": [
            "Go to Documents, change notas.txt to resumen.txt and move it onto the Desktop.",
            "Open Documents, rename notas.txt → resumen.txt and place it on the Desktop."
        ],
        "baseline_interactions": 14,
        "app_context": "macOS, Finder"
    },
    "TC4": {
        "instruction": "Create a sheet with 'Gastos,120,80' in the first row and save it as 'presupuesto.csv' in Documents.",
        "paraphrases": [
            "Write 'Gastos,120,80' as the first row and save as presupuesto.csv in Documents.",
            "Make a CSV with the row Gastos,120,80 and store it under Documents as presupuesto.csv."
        ],
        "baseline_interactions": 22,
        "app_context": "macOS, TextEdit (CSV)"
    },
    "TC5": {
        "instruction": "Open https://example.com, copy the visible page content, paste it into a new text file, and save it as 'contenido.txt' in Documents.",
        "paraphrases": [
            "Go to example.com, copy the main text on the page, paste into a new text file, save as contenido.txt under Documents.",
            "Open example.com, select all page content, copy, paste to a new text file, and store as contenido.txt in Documents."
        ],
        "baseline_interactions": 26,
        "app_context": "macOS, Safari + TextEdit"
    },
    "TC6": {
        "instruction": "Create a txt file containing 'reunión lunes 9am', save it in Documents as 'agenda.txt' and then open it.",
        "paraphrases": [
            "Make a text file with 'reunión lunes 9am', save it in Docs as agenda.txt and open it.",
            "Create a text file that says 'reunión lunes 9am', store it in Documents as agenda.txt and open."
        ],
        "baseline_interactions": 20,
        "app_context": "macOS, TextEdit + Finder"
    },
    "TC7": {
        "instruction": "Create a new text file with two lines: 'Línea 1' and 'Línea 2', and save it as 'dos_lineas.txt' in Documents.",
        "paraphrases": [
            "Make a new text with two lines (Línea 1 / Línea 2) and save it as dos_lineas.txt in Documents.",
            "Write two lines 'Línea 1' then 'Línea 2' and save to Documents as dos_lineas.txt."
        ],
        "baseline_interactions": 18,
        "app_context": "macOS, TextEdit"
    },
    "TC8": {
        "instruction": "Open 'agenda.txt' from Documents and append the line 'ubicación: sala 3'. Save changes.",
        "paraphrases": [
            "Open agenda.txt in Documents and add 'ubicación: sala 3' at the end, then save.",
            "Open the file agenda.txt under Documents, append 'ubicación: sala 3' and save."
        ],
        "baseline_interactions": 16,
        "app_context": "macOS, Finder + TextEdit"
    },
    "TC9": {
        "instruction": "Move 'dos_lineas.txt' and 'agenda.txt' from Documents to Desktop.",
        "paraphrases": [
            "Take dos_lineas.txt and agenda.txt out of Documents and move them to the Desktop.",
            "Relocate agenda.txt and dos_lineas.txt from Docs to the Desktop."
        ],
        "baseline_interactions": 20,
        "app_context": "macOS, Finder"
    },
    "TC10": {
        "instruction": "Open https://example.com and https://www.iana.org/domains/reserved, copy both page titles, paste them on separate lines in a new text file, and save as 'titulos.txt' in Documents.",
        "paraphrases": [
            "Open example.com and IANA reserved domains page, copy both titles, paste each on a new line, save as titulos.txt under Documents.",
            "Visit example.com and the IANA reserved page, take their titles, paste them line by line, and store as titulos.txt in Documents."
        ],
        "baseline_interactions": 34,
        "app_context": "macOS, Safari + TextEdit"
    },
    "TC11": {
        "instruction": "In Documents, rename 'dos_lineas.txt' to 'dos_lineas.md'.",
        "paraphrases": [
            "Change the extension of dos_lineas.txt to dos_lineas.md in Documents.",
            "Rename dos_lineas.txt as dos_lineas.md under Documents."
        ],
        "baseline_interactions": 10,
        "app_context": "macOS, Finder"
    },
    "TC12": {
        "instruction": "Move 'resumen.txt' from Desktop back to Documents.",
        "paraphrases": [
            "Take resumen.txt from the Desktop and move it into Documents.",
            "Relocate the file resumen.txt from Desktop to Documents."
        ],
        "baseline_interactions": 12,
        "app_context": "macOS, Finder"
    },
    "TC13": {
        "instruction": "Create a CSV with two rows: 'Item,10,5' and 'Total,15,0' and save it as 'valores.csv' in Documents.",
        "paraphrases": [
            "Make a CSV with lines Item,10,5 and Total,15,0, then save as valores.csv in Documents.",
            "Write two rows (Item,10,5 / Total,15,0) and store in Documents as valores.csv."
        ],
        "baseline_interactions": 24,
        "app_context": "macOS, TextEdit (CSV)"
    },
    "TC14": {
        "instruction": "Open https://www.example.com and save the page title into 'titulo_example.txt' under Documents.",
        "paraphrases": [
            "Visit example.com and store its title into titulo_example.txt in Documents.",
            "Open the example.com site and write the page title to a file called titulo_example.txt in Documents."
        ],
        "baseline_interactions": 20,
        "app_context": "macOS, Safari + TextEdit"
    },
    "TC15": {
        "instruction": "Create a text file with three lines: 'tarea1', 'tarea2', 'tarea3' and save as 'todo.txt' in Documents.",
        "paraphrases": [
            "Write three lines (tarea1, tarea2, tarea3) into a new text file and save it as todo.txt in Documents.",
            "Make a text with tareas (1..3) each on its line; save to Documents as todo.txt."
        ],
        "baseline_interactions": 18,
        "app_context": "macOS, TextEdit"
    },
    "TC16": {
        "instruction": "Open 'todo.txt' from Documents.",
        "paraphrases": [
            "Open the file todo.txt stored in Documents.",
            "Open Documents/todo.txt."
        ],
        "baseline_interactions": 8,
        "app_context": "macOS, Finder"
    },
    "TC17": {
        "instruction": "Open https://example.com, copy the current URL from the address bar, paste it into a new text file, and save as 'url.txt' in Documents.",
        "paraphrases": [
            "Go to example.com, copy the address bar URL, paste to a new text file, save it as url.txt under Documents.",
            "Open example.com, grab the URL from the location bar, paste in a text file, store as url.txt in Documents."
        ],
        "baseline_interactions": 24,
        "app_context": "macOS, Safari + TextEdit"
    },
    "TC18": {
        "instruction": "Create a text file containing 'Resumen del proyecto: pendiente' and save as 'resumen_proyecto.txt' in Documents.",
        "paraphrases": [
            "Make a text with 'Resumen del proyecto: pendiente' and save to Documents as resumen_proyecto.txt.",
            "Write 'Resumen del proyecto: pendiente' into a new file and store it as resumen_proyecto.txt under Documents."
        ],
        "baseline_interactions": 16,
        "app_context": "macOS, TextEdit"
    },
    "TC19": {
        "instruction": "Open 'informe semanal.txt' from Documents.",
        "paraphrases": [
            "Open the file named 'informe semanal.txt' under Documents.",
            "In Documents, open informe semanal.txt."
        ],
        "baseline_interactions": 8,
        "app_context": "macOS, Finder"
    },
    "TC20": {
        "instruction": "Open https://example.com, copy the page title, then create a CSV with 'Title,<PASTE_TITLE>' as the first row and save as 'titulo_web.csv' in Documents.",
        "paraphrases": [
            "Visit example.com, grab the title, then create a CSV having first row Title,<PASTE_TITLE> and save it as titulo_web.csv in Documents.",
            "Go to example.com, copy the page title and build a CSV with 'Title,<PASTE_TITLE>' stored as titulo_web.csv in Documents."
        ],
        "baseline_interactions": 28,
        "app_context": "macOS, Safari + TextEdit"
    },
    "TC21": {
        "instruction": "Create a text file with three lines 'nota A', 'nota B', 'nota C' and save it as 'notas3.txt' in Documents.",
        "paraphrases": [
            "Write lines nota A/B/C into a new text file and save as notas3.txt in Documents.",
            "Make a text of three lines (nota A, nota B, nota C) and store as notas3.txt under Documents."
        ],
        "baseline_interactions": 18,
        "app_context": "macOS, TextEdit"
    },
    "TC22": {
        "instruction": "Open https://www.iana.org/domains/reserved, copy the page title, and save it into 'titulo_iana.txt' in Documents.",
        "paraphrases": [
            "Visit the IANA reserved page, copy its title and store into titulo_iana.txt under Documents.",
            "Open IANA reserved domains page, grab the title and write to titulo_iana.txt in Documents."
        ],
        "baseline_interactions": 22,
        "app_context": "macOS, Safari + TextEdit"
    },
    "TC23": {
        "instruction": "Open 'todo.txt' from Documents, copy all its content, paste into a new text file and save it as 'todo_copy.txt' in Documents.",
        "paraphrases": [
            "Open Documents/todo.txt, select all and copy, create a new text file, paste and save as todo_copy.txt in Documents.",
            "Open todo.txt, copy everything, paste into a new file and save under Documents as todo_copy.txt."
        ],
        "baseline_interactions": 22,
        "app_context": "macOS, Finder + TextEdit"
    },
    "TC24": {
        "instruction": "Move 'resumen.txt' from Desktop to Documents and rename it to 'resumen_final.txt'.",
        "paraphrases": [
            "Take resumen.txt on Desktop, move it to Documents and rename to resumen_final.txt.",
            "Relocate the file resumen.txt from Desktop to Documents and change its name to resumen_final.txt."
        ],
        "baseline_interactions": 16,
        "app_context": "macOS, Finder"
    },
    "TC25": {
        "instruction": "Create a CSV with header 'Name,Score' and a row 'Alice,95', save as 'scores.csv' in Documents.",
        "paraphrases": [
            "Write a CSV header Name,Score with a line Alice,95 and store as scores.csv in Documents.",
            "Make a CSV: first line Name,Score; second line Alice,95; save to Documents as scores.csv."
        ],
        "baseline_interactions": 22,
        "app_context": "macOS, TextEdit (CSV)"
    },
    "TC26": {
        "instruction": "Open https://example.com, copy the page title, open 'titulos.txt' in Documents and append the title as a new line, then save.",
        "paraphrases": [
            "Go to example.com, grab the title, append it to Documents/titulos.txt on a new line and save.",
            "Open example.com, copy page title and add it to the end of titulos.txt under Documents."
        ],
        "baseline_interactions": 28,
        "app_context": "macOS, Safari + TextEdit"
    },
    "TC27": {
        "instruction": "Create a text file with the paragraph 'Este es un memo. Contiene varias oraciones.' and save as 'memo.txt' in Documents.",
        "paraphrases": [
            "Write a paragraph memo with multiple sentences and save it as memo.txt in Documents.",
            "Make a text file containing 'Este es un memo. Contiene varias oraciones.' and store under Documents as memo.txt."
        ],
        "baseline_interactions": 16,
        "app_context": "macOS, TextEdit"
    },
    "TC28": {
        "instruction": "Open 'notas.txt' from Documents.",
        "paraphrases": [
            "Open the file notas.txt under Documents.",
            "In Documents, open notas.txt."
        ],
        "baseline_interactions": 8,
        "app_context": "macOS, Finder"
    },
    "TC29": {
        "instruction": "Create a text 'meeting 10:30' saved as 'meeting.txt' in Documents, then move it to Desktop.",
        "paraphrases": [
            "Write 'meeting 10:30' to a new file meeting.txt in Documents and then move it onto Desktop.",
            "Create meeting.txt with 'meeting 10:30' under Documents, then place it on the Desktop."
        ],
        "baseline_interactions": 20,
        "app_context": "macOS, TextEdit + Finder"
    },
    "TC30": {
        "instruction": "Open https://www.iana.org/domains/reserved, copy the title and create a CSV with 'Title,<PASTE_TITLE>' saved as 'title_iana.csv' in Documents.",
        "paraphrases": [
            "Visit the IANA reserved page, grab the title and build a CSV first row Title,<PASTE_TITLE>, save to Documents as title_iana.csv.",
            "Open IANA reserved page, copy the title and store it in a CSV called title_iana.csv in Documents."
        ],
        "baseline_interactions": 28,
        "app_context": "macOS, Safari + TextEdit"
    },
    "TC31": {
        "instruction": "Create a text file with three lines '1) uno', '2) dos', '3) tres' and save as 'lista.txt' in Documents.",
        "paraphrases": [
            "Write three numbered lines (1) uno / 2) dos / 3) tres) and save as lista.txt in Documents.",
            "Make a text with lines 1) uno, 2) dos, 3) tres and store it as lista.txt under Documents."
        ],
        "baseline_interactions": 18,
        "app_context": "macOS, TextEdit"
    },
    "TC32": {
        "instruction": "In Documents, rename 'todo.txt' to 'todo_old.txt'.",
        "paraphrases": [
            "Change the name of todo.txt to todo_old.txt in Documents.",
            "Rename the file todo.txt as todo_old.txt under Documents."
        ],
        "baseline_interactions": 10,
        "app_context": "macOS, Finder"
    },
    "TC33": {
        "instruction": "Move 'valores.csv' from Documents to Desktop, then move it back to Documents.",
        "paraphrases": [
            "Take valores.csv to the Desktop and then return it to Documents.",
            "Relocate valores.csv from Documents → Desktop and later Desktop → Documents."
        ],
        "baseline_interactions": 24,
        "app_context": "macOS, Finder"
    },
    "TC34": {
        "instruction": "Open https://example.com and https://www.iana.org/domains/reserved, copy both page titles and save them as 'A: <title1>' and 'B: <title2>' in a new text file 'titulos2.txt' in Documents.",
        "paraphrases": [
            "Visit example.com and IANA reserved, copy both titles, write lines A: <title1> and B: <title2>, save as titulos2.txt in Documents.",
            "Open example.com + IANA page, grab the titles and store them prefixed as A:/B: in titulos2.txt under Documents."
        ],
        "baseline_interactions": 34,
        "app_context": "macOS, Safari + TextEdit"
    },
    "TC35": {
        "instruction": "Create a text file containing '{\"status\":\"ok\",\"count\":3}' and save it as 'data.json' in Documents.",
        "paraphrases": [
            "Write the JSON-like text {\"status\":\"ok\",\"count\":3} and store it as data.json in Documents.",
            "Create a file with text {\"status\":\"ok\",\"count\":3} saved to Documents as data.json."
        ],
        "baseline_interactions": 16,
        "app_context": "macOS, TextEdit"
    },
    "TC36": {
        "instruction": "Open 'resumen_proyecto.txt' in Documents, append a new line 'fin' and save.",
        "paraphrases": [
            "Open Documents/resumen_proyecto.txt, add 'fin' at the end and save.",
            "Open the file resumen_proyecto.txt under Documents, append fin and store changes."
        ],
        "baseline_interactions": 14,
        "app_context": "macOS, Finder + TextEdit"
    },
    "TC37": {
        "instruction": "Open 'resumen.txt' from Desktop.",
        "paraphrases": [
            "Open the file resumen.txt that is on Desktop.",
            "On the Desktop, open resumen.txt."
        ],
        "baseline_interactions": 8,
        "app_context": "macOS, Finder"
    },
    "TC38": {
        "instruction": "Create a text file containing 'España, año, acción, último' and save it as 'international.txt' in Documents.",
        "paraphrases": [
            "Write 'España, año, acción, último' to a new file and save as international.txt in Documents.",
            "Create a text with accented words (España, año, acción, último) and store it as international.txt under Documents."
        ],
        "baseline_interactions": 16,
        "app_context": "macOS, TextEdit"
    },
    "TC39": {
        "instruction": "Create a CSV with rows 'A,1', 'B,2', 'C,3' and save as 'abc.csv' in Documents.",
        "paraphrases": [
            "Write a CSV with three lines A,1 / B,2 / C,3 and store it as abc.csv in Documents.",
            "Make a file with lines A,1; B,2; C,3 (comma-separated) saved to Documents as abc.csv."
        ],
        "baseline_interactions": 24,
        "app_context": "macOS, TextEdit (CSV)"
    },
    "TC40": {
        "instruction": "Create a tab-separated file with 'col1\\tcol2' and save as 'table.tsv' in Documents.",
        "paraphrases": [
            "Write a TSV with two columns col1 and col2 separated by a tab, store it as table.tsv in Documents.",
            "Make a file containing 'col1\\tcol2' and save to Documents named table.tsv."
        ],
        "baseline_interactions": 18,
        "app_context": "macOS, TextEdit (TSV)"
    }
}

def call_llm_planner(user_instruction: str) -> str:
    """
    Llama al LLM para obtener un PLAN JSON (response_format JSON).
    """
    if not os.getenv("OPENAI_API_KEY"):
        raise RuntimeError("OPENAI_API_KEY not set in environment.")

    with PLANNER_SYSTEM.open("r", encoding="utf-8") as f:
        system_prompt = f.read()

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_instruction},
    ]

    client = OpenAI()
    resp = client.chat.completions.create(
        model="gpt-4o",
        messages=messages,
        temperature=0.0,
        max_tokens=600,
        response_format={"type": "json_object"}
    )
    return resp.choices[0].message.content

def load_schema():
    with SCHEMA_PATH.open("r", encoding="utf-8") as f:
        return json.load(f)

def parse_and_validate(json_text: str, schema: dict, original_instruction: str, client_for_repair=None):
    try:
        plan = json.loads(json_text)
    except json.JSONDecodeError:
        m = re.search(r"\{.*\}", json_text, re.DOTALL)
        if not m:
            raise ValueError("No JSON object found in LLM output.")
        plan = json.loads(m.group(0))

    if "task" not in plan or not plan["task"]:
        plan["task"] = original_instruction

    try:
        validate(instance=plan, schema=schema)
        return plan
    except ValidationError as e:
        if client_for_repair is None:
            raise

        repair_prompt = (
            "Given this invalid JSON and the schema requirements, "
            "fix the JSON to satisfy the schema strictly. "
            "Return ONLY a valid JSON object, no comments or text.\n\n"
            f"Invalid JSON:\n{json.dumps(plan)}"
        )
        client = client_for_repair
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You fix JSON plans to satisfy a given schema. Output JSON only."},
                {"role": "user", "content": repair_prompt}
            ],
            response_format={"type": "json_object"},
            temperature=0.0,
            max_tokens=700
        )
        fixed = resp.choices[0].message.content
        plan2 = json.loads(fixed)

        if "task" not in plan2 or not plan2["task"]:
            plan2["task"] = original_instruction

        validate(instance=plan2, schema=schema)
        return plan2

def run_osascript(script: str, dry: bool=False):
    if not dry:
        subprocess.run(["osascript", "-e", script])

def save_textedit_as(filename, folder="Documents", dry=False):
    script = textwrap.dedent(f'''
    tell application "TextEdit"
        activate
        try
            save document 1 in (POSIX file ("{os.path.expanduser("~")}/{folder}/{filename}"))
        on error
            delay 0.2
            tell application "System Events"
                keystroke "s" using {{command down}}
                delay 0.3
                keystroke "{filename}"
                delay 0.3
                keystroke "g" using {{command down, shift down}}
                delay 0.3
                keystroke "{folder}"
                keystroke return
                delay 0.2
                keystroke return
            end tell
        end try
    end tell
    ''')
    run_osascript(script, dry)

def finder_goto_folder(folder_path: str, dry=False):
    script = textwrap.dedent(f'''
    tell application "Finder"
        activate
        delay 0.2
        tell application "System Events"
            keystroke "g" using {{command down, shift down}}
            delay 0.2
            keystroke "{folder_path}"
            keystroke return
        end tell
    end tell
    ''')
    run_osascript(script, dry)

def finder_rename_and_move(filename: str, src_folder: str, dst_folder: str, new_name: str=None, dry=False):
    if new_name is None:
        new_name = filename
    script = textwrap.dedent(f'''
    set srcFolder to POSIX file ("{os.path.expanduser("~")}/{src_folder}/") as alias
    set dstFolder to POSIX file ("{os.path.expanduser("~")}/{dst_folder}/") as alias
    tell application "Finder"
        activate
        try
            set theFile to first file of folder srcFolder whose name is "{filename}"
            set name of theFile to "{new_name}"
            move theFile to folder dstFolder with replacing
        on error eMsg
            error eMsg
        end try
    end tell
    ''')
    run_osascript(script, dry)

def safari_copy_title_to_clipboard(dry=False):
    script = textwrap.dedent('''
    tell application "Safari"
        if not (exists document 1) then return
        set t to name of document 1
    end tell
    set the clipboard to t
    ''')
    run_osascript(script, dry)

def open_file_in_finder(folder: str, filename: str, dry=False):
    script = textwrap.dedent(f'''
    set tgtFolder to POSIX file ("{os.path.expanduser("~")}/{folder}/") as alias
    tell application "Finder"
        activate
        try
            open file "{filename}" of folder tgtFolder
        on error eMsg
            error eMsg
        end try
    end tell
    ''')
    run_osascript(script, dry)

def execute_plan(plan: dict, dry: bool=False) -> (bool, str, int):
    interactions = 0
    try:
        for step in plan.get("steps", []):
            action = step.get("action")
            if not action:
                continue

            if action == "wait":
                time.sleep(step.get("timeout_ms", 400) / 1000.0)

            elif action == "hotkey":
                keys = step.get("keys", [])
                if not keys:
                    continue
                if not dry:
                    pyautogui.hotkey(*keys)
                interactions += 1
                time.sleep(0.1)

            elif action == "type":
                if not dry:
                    pyautogui.typewrite(step.get("text", ""), interval=0.02)
                interactions += 1

            elif action == "press":
                if not dry:
                    pyautogui.press(step.get("key", "enter"))
                interactions += 1

            elif action == "open_application":
                app = step.get("target", "TextEdit")
                if not dry:
                    subprocess.run(["open", "-a", app])
                    time.sleep(0.8)
                interactions += 1

            elif action == "open_url":
                url = step.get("target")
                browser = step.get("application", "Safari")
                if url:
                    if not dry:
                        if browser.lower() == "safari":
                            subprocess.run(["open", "-a", "Safari", url])
                        else:
                            subprocess.run(["open", "-a", "Google Chrome", url])
                        time.sleep(1.0)
                    interactions += 1

            elif action == "save_file":
                fname = step.get("filename", "untitled.txt")
                folder = step.get("folder", "Documents")
                if not dry:
                    save_textedit_as(fname, folder, dry=False)
                interactions += 1

            elif action == "focus_window":
                if not dry:
                    pyautogui.hotkey("command", "tab")
                    time.sleep(0.2)
                interactions += 1

            elif action == "goto_folder":
                path = step.get("target", "~/Documents")
                if not dry:
                    finder_goto_folder(path, dry=False)
                    time.sleep(0.4)
                interactions += 1

            elif action == "rename_and_move":
                filename = step.get("filename", "")
                new_name = step.get("new_name", None)
                src_folder = step.get("src_folder", "Documents")
                dst_folder = step.get("dst_folder", "Desktop")
                if not dry:
                    finder_rename_and_move(filename, src_folder, dst_folder, new_name=new_name, dry=False)
                    time.sleep(0.5)
                interactions += 1

            elif action == "copy_page_title":
                if not dry:
                    safari_copy_title_to_clipboard(dry=False)
                    time.sleep(0.2)
                interactions += 1

            elif action == "type_clipboard":
                if not dry:
                    pyautogui.hotkey("command", "v")
                interactions += 1

            elif action == "open_file":
                folder = step.get("folder", "Documents")
                filename = step.get("filename", "")
                if not dry and filename:
                    open_file_in_finder(folder, filename, dry=False)
                    time.sleep(0.5)
                interactions += 1

            else:
                pass

        return True, "", interactions

    except Exception as e:
        return False, str(e), interactions

def log_row(row: dict):
    write_header = not OUT_CSV.exists()
    with OUT_CSV.open("a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(row.keys()))
        if write_header:
            writer.writeheader()
        writer.writerow(row)

def compute_effort(baseline, system):
    try:
        if baseline and baseline > 0 and system is not None:
            return (baseline - system) / baseline * 100.0
    except Exception:
        pass
    return ""

def run_case(tc_key: str, use_paraphrase: bool=False, dry: bool=False):
    schema = load_schema()
    meta = TEST_CASES[tc_key]
    instr = meta["instruction"]
    if use_paraphrase and meta.get("paraphrases"):
        instr = random.choice(meta["paraphrases"])

    t0 = time.perf_counter()

    raw = call_llm_planner(instr)

    try:
        (BASE_DIR / "last_llm_raw.json").write_text(raw, encoding="utf-8")
    except Exception:
        pass

    repair_client = OpenAI()

    try:
        plan = parse_and_validate(raw, schema, original_instruction=instr, client_for_repair=repair_client)
    except Exception as e:
        t1 = time.perf_counter()
        latency = int((t1 - t0) * 1000)
        row = {
            "run_id": datetime.now().strftime("%Y%m%d_%H%M%S"),
            "test_case": tc_key,
            "instruction": instr,
            "paraphrase_of": tc_key if use_paraphrase else "",
            "app_context": meta.get("app_context", "macOS"),
            "baseline_interactions": meta.get("baseline_interactions", ""),
            "system_interactions": "",
            "effort_saved_pct": "",
            "success": 0,
            "latency_ms": latency,
            "error_type": "interpretation_error",
            "notes": str(e)
        }
        log_row(row)
        print(f"[{tc_key}] Interpretation failed:", e)
        return

    ok, err, interactions = execute_plan(plan, dry=dry)

    t1 = time.perf_counter()
    latency = int((t1 - t0) * 1000)

    row = {
        "run_id": datetime.now().strftime("%Y%m%d_%H%M%S"),
        "test_case": tc_key,
        "instruction": instr,
        "paraphrase_of": tc_key if use_paraphrase else "",
        "app_context": meta.get("app_context", "macOS"),
        "baseline_interactions": meta.get("baseline_interactions", ""),
        "system_interactions": interactions,
        "effort_saved_pct": compute_effort(meta.get("baseline_interactions", 0), interactions),
        "success": 1 if ok else 0,
        "latency_ms": latency,
        "error_type": "" if ok else "exec_step_fail",
        "notes": err
    }
    log_row(row)
    print(f"[{tc_key}] Run:", row)

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--runs", type=int, default=2, help="Runs per test case (canonical)")
    ap.add_argument("--par_runs", type=int, default=1, help="Runs per test case (paraphrase)")
    ap.add_argument("--include", nargs="*", default=list(TEST_CASES.keys()), help="Which test cases to include")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    print("WARNING (macOS): This will move your mouse and type. Ensure Accessibility permissions are granted.")
    confirm = input("Type YES to continue: ").strip().upper()
    if confirm != "YES":
        print("Aborted."); raise SystemExit

    for tc in args.include:
        for _ in range(args.runs):
            run_case(tc, use_paraphrase=False, dry=args.dry_run)
        for _ in range(args.par_runs):
            run_case(tc, use_paraphrase=True, dry=args.dry_run)


