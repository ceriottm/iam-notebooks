#!/usr/bin/env python3
# This is an AI generated script that modifies notebooks to create a "grading" version 
# that facilitates going through a list of solutions from students

import argparse
import json
import re
from pathlib import Path


def s(text: str):
    lines = text.split("\n")
    return [l + "\n" for l in lines[:-1]] + [lines[-1]]


def code_cell(src: str):
    return {"cell_type": "code", "execution_count": None, "metadata": {}, "outputs": [], "source": s(src)}


def md_cell(src: str):
    return {"cell_type": "markdown", "metadata": {}, "source": s(src)}


def detect_module_prefix(nb):
    for c in nb["cells"]:
        src = "".join(c.get("source", []))
        m = re.search(r'ExerciseRegistry\(filename_prefix="([^"]+)"\)', src)
        if m:
            return m.group(1)
    return None


def detect_existing_config_value(nb, name: str):
    pattern = re.compile(rf"{re.escape(name)}\s*=\s*\"([^\"]+)\"")
    for c in nb["cells"]:
        src = "".join(c.get("source", []))
        m = pattern.search(src)
        if m:
            return m.group(1)
    return None


def detect_submissions_dir(nb, module_prefix: str):
    submissions_root = Path("submissions")
    if submissions_root.exists():
        matches = sorted(submissions_root.rglob(f"{module_prefix}-*.json"))
        dirs = sorted({m.parent.as_posix() for m in matches})
        if len(dirs) == 1:
            return dirs[0]

    existing = detect_existing_config_value(nb, "_SUBMISSIONS_DIR")
    if existing:
        existing_path = Path(existing)
        if existing_path.is_absolute():
            try:
                return existing_path.relative_to(Path.cwd()).as_posix()
            except ValueError:
                return existing
        return existing

    return "submissions/lab2"


def detect_code_demos(nb):
    mapping = {}
    for c in nb["cells"]:
        src = "".join(c.get("source", []))
        matches = list(re.finditer(r"(\w+)\s*=\s*CodeExercise\(", src))
        for idx, m in enumerate(matches):
            var = m.group(1)
            end = matches[idx + 1].start() if idx + 1 < len(matches) else len(src)
            block = src[m.start():end]
            km = re.search(r'key\s*=\s*"([^"]+)"', block)
            if km and "exercise_registry=exercise_registry" in re.sub(r"\s+", "", block):
                mapping[var] = km.group(1)
    return mapping


def detect_exercise_order(cells):
    order = []
    seen = set()
    for c in cells:
        src = "".join(c.get("source", []))
        matches = list(re.finditer(r"(\w+)\s*=\s*(CodeExercise|TextExercise)\(", src))
        for idx, m in enumerate(matches):
            end = matches[idx + 1].start() if idx + 1 < len(matches) else len(src)
            block = src[m.start():end]
            km = re.search(r'key\s*=\s*"([^"]+)"', block)
            if not km:
                continue
            if "exercise_registry=exercise_registry" not in re.sub(r"\s+", "", block):
                continue
            key = km.group(1)
            if key == "module-summary" or key in seen:
                continue
            seen.add(key)
            order.append(key)
    return order


def remove_previous_patch(cells):
    out = []
    skip_summary_code = False
    for c in cells:
        src = "".join(c.get("source", []))
        if "GRADING MODE — run after creating exercise_registry/check_registry" in src:
            continue
        if "# === AUTO-GRADING-SECTION ===" in src:
            continue
        if src.strip().startswith("# Student Navigation") and "_nav_prev" in src:
            continue
        if src.strip().startswith("## Grading Assistant"):
            continue
        if "display(_build_grading_panel(" in src:
            continue
        if "display(_build_code_score_panel(" in src:
            continue
        if src.strip() == "## Grades Summary":
            skip_summary_code = True
            continue
        if skip_summary_code:
            skip_summary_code = False
            continue
        out.append(c)
    return out


def insert_setup_and_nav(cells, module_prefix, submissions_dir, reference_dir, grades_csv):
    setup = f'''# ═══════════════════════════════════════════════════════════════
# GRADING MODE — run after creating exercise_registry/check_registry
# ═══════════════════════════════════════════════════════════════
import json as _json
import csv as _csv
import glob as _glob
import os as _os
import traceback as _traceback
import ipywidgets as _widgets

_MODULE_PREFIX = "{module_prefix}"
_SUBMISSIONS_DIR = "{submissions_dir}"
_TA_REVIEWS_DIR = _os.path.join(_SUBMISSIONS_DIR, "ta_reviews")
_REFERENCE_DIR = "{reference_dir}"
_GRADES_CSV = "{grades_csv}"

with open(_os.path.join(_REFERENCE_DIR, f"{{_MODULE_PREFIX}}-referenceanswers.json")) as _f:
    _reference_answers = _json.load(_f)

_required_keys = set(_reference_answers.keys())
_student_files = []
_student_names = []
_student_answers_cache = {{}}

_grades = {{}}
_comments = {{}}
if _os.path.exists(_GRADES_CSV):
    with open(_GRADES_CSV, newline="") as _f:
        for _row in _csv.DictReader(_f):
            _grades[(_row["student"], _row["exercise"])] = _row["score"]
            _comments[(_row["student"], _row["exercise"])] = _row.get("comment", "")

def _student_submission_path(name):
    return _os.path.join(_SUBMISSIONS_DIR, f"{{_MODULE_PREFIX}}-{{name}}.json")

def _student_review_path(name):
    return _os.path.join(_TA_REVIEWS_DIR, f"{{_MODULE_PREFIX}}-{{name}}.json")

def _student_active_path(name):
    _review_path = _student_review_path(name)
    if _os.path.exists(_review_path):
        return _review_path
    return _student_submission_path(name)

def _extract_answer_fields(answer):
    if not isinstance(answer, dict):
        return {{}}
    _fields = {{}}
    for _key in ("textarea", "code", "parameters_panel", "selection"):
        if _key in answer:
            _fields[_key] = answer.get(_key)
    return _fields

def _format_code_comment_block(comment):
    if not comment:
        return ""
    _lines = str(comment).splitlines()
    _prefixed = ["# TA comment"] + [f"# {{line}}" if line else "#" for line in _lines]
    return "\\n".join(_prefixed)

def _merge_answer_with_comment(answer_fields, comment):
    _entry = dict(answer_fields)
    _comment = "" if comment is None else str(comment)

    if "textarea" in _entry:
        _base = (_entry.get("textarea") or "").rstrip()
        if _comment:
            _entry["textarea"] = f"{{_base}}\\n\\nTA comment:\\n{{_comment}}" if _base else f"TA comment:\\n{{_comment}}"
        else:
            _entry["textarea"] = _base

    if "code" in _entry and _entry.get("code") is not None:
        _base = (_entry.get("code") or "").rstrip()
        if _comment:
            _comment_block = _format_code_comment_block(_comment)
            _entry["code"] = f"{{_base}}\\n\\n{{_comment_block}}\\n" if _base else f"{{_comment_block}}\\n"
        else:
            _entry["code"] = _base

    return _entry

def _normalize_loaded_answer(answer):
    if not isinstance(answer, dict):
        return answer
    _raw = answer.get("ta_raw_answer")
    if not isinstance(_raw, dict):
        return answer
    _normalized = dict(answer)
    for _key, _value in _raw.items():
        _normalized[_key] = _value
    return _normalized

def _load_student_file_raw(name):
    _path = _student_active_path(name)
    if not _os.path.exists(_path):
        return {{}}
    with open(_path) as _f:
        return _json.load(_f)

def _load_student_file(name):
    _raw_answers = _load_student_file_raw(name)
    return {{_k: _normalize_loaded_answer(_v) for _k, _v in _raw_answers.items()}}

def _save_grades():
    with open(_GRADES_CSV, "w", newline="") as _f:
        w = _csv.DictWriter(_f, fieldnames=["student", "exercise", "score", "comment"])
        w.writeheader()
        for stu, ex in sorted(set(_grades) | set(_comments)):
            w.writerow({{
                "student": stu,
                "exercise": ex,
                "score": _grades.get((stu, ex), ""),
                "comment": _comments.get((stu, ex), ""),
            }})

def _save_review(ex_key, score, comment):
    name = _current_student()
    if name is None:
        raise ValueError("No student selected")
    _grades[(name, ex_key)] = score
    _comments[(name, ex_key)] = comment
    _save_review_entry(ex_key, score=score, comment=comment)
    _save_grades()
    return name

def _save_review_entry(ex_key, score=None, comment=None, answer=None):
    name = _current_student()
    if name is None:
        raise ValueError("No student selected")
    _answers = dict(_load_student_file_raw(name))
    _existing = _answers.get(ex_key, {{}})
    _existing_normalized = _normalize_loaded_answer(_existing)
    _ta_comment = _existing.get("ta_comment", "") if isinstance(_existing, dict) else ""
    _ta_score = _existing.get("ta_score", "") if isinstance(_existing, dict) else ""

    if answer is not None:
        _base_answer = _extract_answer_fields(answer)
    elif isinstance(_existing_normalized, dict):
        _base_answer = _extract_answer_fields(_existing_normalized)
    else:
        _base_answer = {{}}

    _comment = _ta_comment if comment is None else comment
    _score = _ta_score if score is None else score

    _entry = _merge_answer_with_comment(_base_answer, _comment)

    if _base_answer:
        _entry["ta_raw_answer"] = _base_answer
    if _comment is not None:
        _entry["ta_comment"] = _comment
    if _score is not None:
        _entry["ta_score"] = _score

    _answers[ex_key] = _entry

    _os.makedirs(_TA_REVIEWS_DIR, exist_ok=True)
    _fp = _student_review_path(name)
    with open(_fp, "w") as _f:
        _json.dump(_answers, _f, indent=2, ensure_ascii=False)
        _f.write("\\n")

    _student_answers_cache[name] = _answers
    _current_student_answers["value"] = _answers
    return name

def _save_current_student_answer(ex_key):
    if ex_key not in _code_widget_panels:
        raise KeyError(f"Unknown code panel: {{ex_key}}")

    _template_widget, _container, _student_widget = _code_widget_panels[ex_key]
    if _student_widget is None:
        raise ValueError(f"No loaded student widget for {{ex_key}}")

    return _save_review_entry(ex_key, answer=_student_widget.answer)

_ref_exercise_registry = ExerciseRegistry(filename_prefix=_MODULE_PREFIX)
for _k in sorted(k for k in _required_keys if not k.endswith('-function')):
    TextExercise(description="", key=_k, title=_k, exercise_registry=_ref_exercise_registry)

_student_idx = {{"value": 0}}
_ref_loaded = {{"value": False}}
_current_student_answers = {{"value": {{}}}}

def _current_student():
    return _student_names[_student_idx["value"]] if _student_names else None

def _refresh_student_cache(force=False):
    global _student_files, _student_names, _student_answers_cache
    _files = sorted(_glob.glob(_os.path.join(_SUBMISSIONS_DIR, f"{{_MODULE_PREFIX}}-*.json")))
    if (not force) and _files == _student_files:
        return

    _old_name = _current_student()
    _student_files = _files
    _student_names = [
        _os.path.basename(f).replace(f"{{_MODULE_PREFIX}}-", "").replace(".json", "")
        for f in _student_files
    ]
    _student_answers_cache = {{}}
    for _fp, _name in zip(_student_files, _student_names):
        try:
            _student_answers_cache[_name] = _load_student_file(_name)
        except Exception:
            _student_answers_cache[_name] = {{}}

    _nav_dropdown.options = [(f"{{i+1}}. {{n}}", i) for i, n in enumerate(_student_names)]
    if not _student_names:
        _student_idx["value"] = 0
        _nav_dropdown.value = None
        return

    if _old_name in _student_names:
        _student_idx["value"] = _student_names.index(_old_name)
    else:
        _student_idx["value"] = min(_student_idx["value"], len(_student_names) - 1)
    _nav_dropdown.value = _student_idx["value"]

def _ensure_dropdown_has_file(registry, filepath):
    opts = list(registry._answers_files_dropdown.options)
    if filepath not in opts:
        opts.insert(max(0, len(opts)-1), filepath)
        registry._answers_files_dropdown.options = opts

def _apply_answer_if_compatible(widget, answer):
    if not isinstance(answer, dict):
        return False
    try:
        if "code" in answer and hasattr(widget, "_code"):
            widget.answer = {{
                "code": answer.get("code"),
                "parameters_panel": answer.get("parameters_panel"),
            }}
            return True
        if "textarea" in answer and hasattr(widget, "_textarea"):
            widget.answer = {{"textarea": answer["textarea"]}}
            return True
        if "selection" in answer and hasattr(widget, "_selection_widget"):
            widget.answer = {{"selection": answer["selection"]}}
            return True
    except Exception:
        return False
    return False

def _load_into_registry(registry, filepath, who):
    if not _os.path.exists(filepath):
        raise FileNotFoundError(f"{{who}} file not found: {{filepath}}")
    _ensure_dropdown_has_file(registry, filepath)
    with open(filepath) as _f:
        _answers = _json.load(_f)

    _registered_widgets = registry.registered_widgets
    for _k, _ans in _answers.items():
        _widget = _registered_widgets.get(_k)
        if _widget is not None:
            _apply_answer_if_compatible(_widget, _ans)

    registry._loaded_file_name = filepath
    try:
        registry._answers_files_dropdown.value = filepath
    except Exception:
        pass

def _load_reference():
    _ref_loaded["value"] = True

def _load_current_student():
    _refresh_student_cache()
    name = _current_student()
    if name is None:
        _current_student_answers["value"] = {{}}
        return
    _current_student_answers["value"] = _student_answers_cache.get(name, {{}})

def _clone_widget(_widget):
    from ipywidgets import fixed as _fixed_type
    from ipywidgets import (
        BoundedFloatText,
        BoundedIntText,
        Checkbox,
        Dropdown,
        FloatSlider,
        FloatText,
        IntSlider,
        IntText,
        RadioButtons,
        SelectionSlider,
        Text,
        ToggleButtons,
    )

    if isinstance(_widget, _fixed_type):
        return _fixed_type(_widget.value)
    if isinstance(_widget, IntSlider):
        return IntSlider(
            value=_widget.value,
            min=_widget.min,
            max=_widget.max,
            step=_widget.step,
            description=_widget.description,
            disabled=_widget.disabled,
            continuous_update=_widget.continuous_update,
            orientation=_widget.orientation,
            readout=_widget.readout,
            readout_format=_widget.readout_format,
        )
    if isinstance(_widget, FloatSlider):
        return FloatSlider(
            value=_widget.value,
            min=_widget.min,
            max=_widget.max,
            step=_widget.step,
            description=_widget.description,
            disabled=_widget.disabled,
            continuous_update=_widget.continuous_update,
            orientation=_widget.orientation,
            readout=_widget.readout,
            readout_format=_widget.readout_format,
        )
    if isinstance(_widget, Dropdown):
        return Dropdown(
            options=_widget.options,
            value=_widget.value,
            description=_widget.description,
            disabled=_widget.disabled,
        )
    if isinstance(_widget, SelectionSlider):
        return SelectionSlider(
            options=_widget.options,
            value=_widget.value,
            description=_widget.description,
            disabled=_widget.disabled,
            continuous_update=_widget.continuous_update,
            orientation=_widget.orientation,
            readout=_widget.readout,
        )
    if isinstance(_widget, ToggleButtons):
        return ToggleButtons(
            options=_widget.options,
            value=_widget.value,
            description=_widget.description,
            disabled=_widget.disabled,
        )
    if isinstance(_widget, RadioButtons):
        return RadioButtons(
            options=_widget.options,
            value=_widget.value,
            description=_widget.description,
            disabled=_widget.disabled,
        )
    if isinstance(_widget, Checkbox):
        return Checkbox(
            value=_widget.value,
            description=_widget.description,
            disabled=_widget.disabled,
        )
    if isinstance(_widget, BoundedIntText):
        return BoundedIntText(
            value=_widget.value,
            min=_widget.min,
            max=_widget.max,
            step=_widget.step,
            description=_widget.description,
            disabled=_widget.disabled,
        )
    if isinstance(_widget, BoundedFloatText):
        return BoundedFloatText(
            value=_widget.value,
            min=_widget.min,
            max=_widget.max,
            step=_widget.step,
            description=_widget.description,
            disabled=_widget.disabled,
        )
    if isinstance(_widget, IntText):
        return IntText(
            value=_widget.value,
            description=_widget.description,
            disabled=_widget.disabled,
        )
    if isinstance(_widget, FloatText):
        return FloatText(
            value=_widget.value,
            description=_widget.description,
            disabled=_widget.disabled,
        )
    if isinstance(_widget, Text):
        return Text(
            value=_widget.value,
            description=_widget.description,
            disabled=_widget.disabled,
            placeholder=_widget.placeholder,
        )

    cloned = _widget.__class__()
    for _attr in ("value", "description", "disabled"):
        if hasattr(_widget, _attr) and hasattr(cloned, _attr):
            setattr(cloned, _attr, getattr(_widget, _attr))
    return cloned

def _clone_parameters_panel(student_widget):
    from scwidgets.code import ParametersPanel

    src_panel = student_widget.parameters_panel
    if src_panel is None:
        return None
    cloned = {{}}
    for pname, _widget in src_panel.param_to_widget_map.items():
        cloned[pname] = _clone_widget(_widget)
    return ParametersPanel(**cloned)

def _clone_outputs(student_widget):
    from scwidgets.cue import CueFigure, CueObject
    import matplotlib.pyplot as _plt

    cloned = []
    for _output in student_widget.outputs:
        if isinstance(_output, CueFigure):
            _figure = _output.figure
            fig = _plt.figure(
                figsize=_figure.get_size_inches(),
                tight_layout=bool(_figure.get_tight_layout()),
            )
            axes = _figure.get_axes()
            if axes:
                for idx, ax in enumerate(axes, start=1):
                    try:
                        fig.add_subplot(ax.get_subplotspec())
                    except Exception:
                        fig.add_subplot(1, len(axes), idx)
            cloned.append(fig)
        else:
            cloned.append(CueObject())
    return cloned if cloned else [CueObject()]

def _copy_checks(source_widget, target_widget):
    if source_widget._code is None or source_widget.check_registry is None:
        return
    for _check in source_widget.checks:
        target_widget.check_registry.add_check(
            target_widget,
            _check.asserts,
            _check.inputs_parameters,
            _check.outputs_references,
            _check.fingerprint,
            getattr(_check, "_suppress_fingerprint_asserts", True),
            getattr(_check, "_stop_on_assert_error_raised", False),
        )

def _make_display_codeexercise(template_widget, title, answer=None, enable_checks=False):
    from scwidgets.code import CodeInput

    # Build an independent code editor (avoid sharing widget state with student panel)
    _sw_code = template_widget._code
    if _sw_code is None:
        display_code = None
    else:
        display_code = CodeInput(
            function_name=_sw_code.function_name,
            function_parameters=_sw_code.function_parameters,
            docstring=_sw_code.docstring if _sw_code._display_docstring else None,
            function_body=_sw_code.function_body,
            builtins=getattr(_sw_code, "_builtins", None),
            code_theme=_sw_code.code_theme,
        )

    ref_params = _clone_parameters_panel(template_widget)
    outs = _clone_outputs(template_widget)
    display_check_registry = CheckRegistry() if enable_checks and _sw_code is not None else None

    widget = CodeExercise(
        code=display_code,
        check_registry=display_check_registry,
        outputs=outs,
        parameters=ref_params,
        update=template_widget._update_func,
        update_mode=template_widget._update_mode,
        description="",
        title=title,
    )
    if display_check_registry is not None:
        _copy_checks(template_widget, widget)
    if answer is not None:
        widget.answer = answer
    return widget

_nav_prev = _widgets.Button(description="◀", layout=_widgets.Layout(width="50px"))
_nav_next = _widgets.Button(description="▶", layout=_widgets.Layout(width="50px"))
_nav_load = _widgets.Button(description="Load Student", button_style="warning", layout=_widgets.Layout(width="130px"))
_nav_dropdown = _widgets.Dropdown(options=[(f"{{i+1}}. {{n}}", i) for i,n in enumerate(_student_names)], value=0 if _student_names else None, layout=_widgets.Layout(width="220px"))
_nav_label = _widgets.HTML(); _nav_status = _widgets.HTML(); _nav_debug_output = _widgets.Output()

def _update_nav_ui():
    idx = _student_idx["value"]; name = _current_student() or "N/A"
    _nav_label.value = f'<b style="font-size:14px;">Student: {{name}} ({{idx+1}}/{{len(_student_names)}})</b>'
    if _student_names and _nav_dropdown.value != idx:
        _nav_dropdown.value = idx

def _switch_to(idx):
    if not _student_names: return
    _student_idx["value"] = idx % len(_student_names)
    _update_nav_ui()

def _load_and_refresh():
    try:
        _refresh_student_cache()
        _load_reference(); _load_current_student(); _update_all_grading_panels()
        _nav_status.value = '<span style="color:green;">✅ loaded</span>'
    except Exception as e:
        _nav_status.value = f'<span style="color:red;">❌ {{e}}</span>'
        _nav_debug_output.clear_output()
        with _nav_debug_output: _traceback.print_exc()

def _load_and_refresh_one(ex_key):
    try:
        _refresh_student_cache()
        _load_reference(); _load_current_student()
        if ex_key in _grading_panels:
            _update_grading_panel(ex_key)
        if ex_key in _code_widget_panels:
            _update_code_widget_panel(ex_key)
        if ex_key in _code_score_panels:
            _update_code_score_panel(ex_key)
        _nav_status.value = '<span style="color:green;">✅ loaded</span>'
    except Exception as e:
        _nav_status.value = f'<span style="color:red;">❌ {{e}}</span>'
        _nav_debug_output.clear_output()
        with _nav_debug_output: _traceback.print_exc()

def _on_nav_prev(_): _switch_to(_student_idx["value"] - 1); _load_and_refresh()
def _on_nav_next(_): _switch_to(_student_idx["value"] + 1); _load_and_refresh()
def _on_nav_load(_): _load_and_refresh()
def _on_dropdown_change(change):
    if change["name"] == "value" and change["new"] is not None and change["new"] != _student_idx["value"]:
        _switch_to(change["new"])

_nav_prev.on_click(_on_nav_prev); _nav_next.on_click(_on_nav_next); _nav_load.on_click(_on_nav_load)
_nav_dropdown.observe(_on_dropdown_change, names="value")
_refresh_student_cache(force=True)
_update_nav_ui()

_grading_panels = {{}}; _code_score_panels = {{}}
_code_widget_panels = {{}}

def _fmt_answer(data):
    parts = []
    if "textarea" in data and data["textarea"]:
        t = data["textarea"].replace('&','&amp;').replace('<','&lt;').replace('>','&gt;')
        parts.append(f'<div style="white-space:pre-wrap;font-size:13px;">{{t}}</div>')
    if "code" in data and data["code"]:
        c = data["code"].replace('&','&amp;').replace('<','&lt;').replace('>','&gt;')
        parts.append(f'<pre style="background:#f5f5f5;padding:8px;border-radius:4px;font-size:12px;overflow-x:auto;">{{c}}</pre>')
    if "parameters_panel" in data and data["parameters_panel"]:
        parts.append(f'<div style="font-size:12px;color:#666;">params: {{data["parameters_panel"]}}</div>')
    return "\\n".join(parts) if parts else '<em style="color:#999;">(empty)</em>'

def _comment_for(name, ex_key):
    if not name:
        return ""
    _answer = _current_student_answers["value"].get(ex_key, {{}})
    if isinstance(_answer, dict) and "ta_comment" in _answer:
        return _answer.get("ta_comment", "")
    return _comments.get((name, ex_key), "")

def _build_grading_panel(ex_key):
    ref_html = _widgets.HTML(layout=_widgets.Layout(width="49%")); stu_html = _widgets.HTML(layout=_widgets.Layout(width="49%"))
    score_input = _widgets.Text(placeholder="Score", layout=_widgets.Layout(width="80px"))
    comment_input = _widgets.Textarea(placeholder="TA comment", layout=_widgets.Layout(width="100%", height="74px"))
    save_btn = _widgets.Button(description="Save Review", button_style="success", layout=_widgets.Layout(width="110px"))
    status = _widgets.HTML(layout=_widgets.Layout(width="420px"))
    prev_btn = _widgets.Button(description="◀ Prev", layout=_widgets.Layout(width="80px"))
    next_btn = _widgets.Button(description="Next ▶", layout=_widgets.Layout(width="80px"))
    stu_label = _widgets.HTML()

    def _on_save(_):
        name = _current_student()
        if name:
            _save_review(ex_key, score_input.value, comment_input.value)
            status.value = f'<span style="color:green;">✅ saved review for {{name}} / {{ex_key}}</span>'
    save_btn.on_click(_on_save)
    prev_btn.on_click(lambda _: (_switch_to(_student_idx["value"] - 1), _load_and_refresh_one(ex_key)))
    next_btn.on_click(lambda _: (_switch_to(_student_idx["value"] + 1), _load_and_refresh_one(ex_key)))

    _grading_panels[ex_key] = (ref_html, stu_html, score_input, comment_input, status, stu_label)
    _update_grading_panel(ex_key)
    row = _widgets.HBox([prev_btn, stu_label, next_btn, _widgets.Label("Score:"), score_input, save_btn, status])
    comment_box = _widgets.VBox([_widgets.HTML("<b>Comment</b>"), comment_input])
    comp = _widgets.HBox([ref_html, stu_html], layout=_widgets.Layout(width="100%", justify_content="space-between"))
    return _widgets.VBox([row, comment_box, comp], layout=_widgets.Layout(border="1px solid #eee", padding="8px", margin="4px 0"))

def _update_grading_panel(ex_key):
    if ex_key not in _grading_panels: return
    ref_html, stu_html, score_input, comment_input, status, stu_label = _grading_panels[ex_key]
    name = _current_student(); idx = _student_idx["value"]
    stu_label.value = f'<b>{{name or "N/A"}} ({{idx+1}}/{{len(_student_names)}})</b>'
    ref_data = _reference_answers.get(ex_key, {{}})
    ref_html.value = ('<div style="border:1px solid #4CAF50;border-radius:6px;padding:10px;min-height:80px;">'
                      '<div style="font-weight:bold;color:#4CAF50;margin-bottom:4px;">📗 Reference</div>'
                      + _fmt_answer(ref_data) + '</div>')
    stu_data = _current_student_answers["value"].get(ex_key, {{}}) if name else {{}}
    stu_html.value = (f'<div style="border:1px solid #2196F3;border-radius:6px;padding:10px;min-height:80px;">'
                      f'<div style="font-weight:bold;color:#2196F3;margin-bottom:4px;">📘 Student ({{name or "N/A"}})</div>'
                      + _fmt_answer(stu_data) + '</div>')
    score_input.value = _grades.get((name, ex_key), "") if name else ""
    comment_input.value = _comment_for(name, ex_key)
    status.value = ""

def _build_code_score_panel(ex_key):
    score_input = _widgets.Text(placeholder="Score", layout=_widgets.Layout(width="80px"))
    comment_input = _widgets.Textarea(placeholder="TA comment", layout=_widgets.Layout(width="100%", height="74px"))
    save_btn = _widgets.Button(description="Save Review", button_style="success", layout=_widgets.Layout(width="110px"))
    save_answer_btn = _widgets.Button(description="Save Edited Answer", button_style="info", layout=_widgets.Layout(width="150px"))
    status = _widgets.HTML(layout=_widgets.Layout(width="420px"))
    prev_btn = _widgets.Button(description="◀ Prev", layout=_widgets.Layout(width="80px"))
    next_btn = _widgets.Button(description="Next ▶", layout=_widgets.Layout(width="80px"))
    stu_label = _widgets.HTML()

    def _on_save_review(_):
        name = _current_student()
        if name:
            _save_review(ex_key, score_input.value, comment_input.value)
            status.value = f'<span style="color:green;">✅ saved review for {{name}} / {{ex_key}}</span>'

    def _on_save_answer(_):
        name = _current_student()
        if name:
            _save_current_student_answer(ex_key)
            status.value = f'<span style="color:green;">✅ saved edited answer for {{name}} / {{ex_key}}</span>'

    save_btn.on_click(_on_save_review)
    save_answer_btn.on_click(_on_save_answer)
    prev_btn.on_click(lambda _: (_switch_to(_student_idx["value"] - 1), _load_and_refresh_one(ex_key)))
    next_btn.on_click(lambda _: (_switch_to(_student_idx["value"] + 1), _load_and_refresh_one(ex_key)))
    _code_score_panels[ex_key] = (score_input, comment_input, status, stu_label)
    _update_code_score_panel(ex_key)
    row = _widgets.HBox([prev_btn, stu_label, next_btn, _widgets.Label("Score:"), score_input, save_btn, save_answer_btn, status])
    comment_box = _widgets.VBox([_widgets.HTML("<b>Comment</b>"), comment_input])
    return _widgets.VBox([row, comment_box])

def _build_code_widget_panel(template_widget, ex_key):
    container = _widgets.VBox()
    _code_widget_panels[ex_key] = (template_widget, container, None)
    _update_code_widget_panel(ex_key)
    return container

def _update_code_widget_panel(ex_key):
    if ex_key not in _code_widget_panels:
        return
    template_widget, container, _current_widget = _code_widget_panels[ex_key]
    ref_widget = _make_display_codeexercise(
        template_widget,
        "Reference",
        _reference_answers.get(ex_key),
    )
    student_name = _current_student()
    student_title = f"Student: {{student_name}}" if student_name else "Student"
    student_answer = _current_student_answers["value"].get(ex_key)
    student_widget = _make_display_codeexercise(
        template_widget,
        student_title,
        student_answer,
        enable_checks=True,
    )
    container.children = [
        _widgets.HBox(
            [ref_widget, student_widget],
            layout=_widgets.Layout(width="100%"),
        )
    ]
    _code_widget_panels[ex_key] = (template_widget, container, student_widget)

def _update_code_score_panel(ex_key):
    if ex_key not in _code_score_panels: return
    score_input, comment_input, status, stu_label = _code_score_panels[ex_key]
    name = _current_student(); idx = _student_idx["value"]
    stu_label.value = f'<b>{{name or "N/A"}} ({{idx+1}}/{{len(_student_names)}})</b>'
    score_input.value = _grades.get((name, ex_key), "") if name else ""
    comment_input.value = _comment_for(name, ex_key)
    status.value = ""

def _update_all_grading_panels():
    for k in list(_grading_panels.keys()): _update_grading_panel(k)
    for k in list(_code_widget_panels.keys()): _update_code_widget_panel(k)
    for k in list(_code_score_panels.keys()): _update_code_score_panel(k)

print(f"✅ Grading mode ready: {{len(_student_names)}} students")
print("Run all cells, then click Load Student.")
'''

    nav_src = '''# Student Navigation
display(_widgets.VBox([
    _widgets.HBox([_nav_prev, _nav_dropdown, _nav_next, _nav_load, _nav_label, _nav_status],
                  layout=_widgets.Layout(border="2px solid #FF9800", padding="8px", border_radius="8px", margin="8px 0", justify_content="center")),
    _nav_debug_output
]))
'''

    # insert after check_registry
    pos = None
    for i, c in enumerate(cells):
        if "check_registry = CheckRegistry()" in "".join(c.get("source", [])):
            pos = i + 1
            break
    if pos is None:
        raise RuntimeError("Cannot find check_registry cell")
    cells.insert(pos, code_cell(setup))
    cells.insert(pos + 1, code_cell(nav_src))


def patch_code_displays(cells, code_demo_to_key):
    # Replace display(exXX_code_demo) with side-by-side + score panel
    for c in cells:
        src = "".join(c.get("source", []))
        for var, key in code_demo_to_key.items():
            pattern = rf"(^|\n)(\s*)display\(\s*{re.escape(var)}\s*\)"
            src = re.sub(
                pattern,
                lambda m, var=var, key=key: (
                    f"{m.group(1)}{m.group(2)}display(_build_code_widget_panel({var}, \"{key}\"))\n"
                    f"{m.group(2)}display(_build_code_score_panel(\"{key}\"))"
                ),
                src,
            )
        c["source"] = s(src)


def add_text_panels(cells):
    inserts = []
    for i, c in enumerate(cells):
        src = "".join(c.get("source", []))
        if "TextExercise(" in src and 'exercise_registry=exercise_registry' in src:
            m = re.search(r'key="([^"]+)"', src)
            if m and not m.group(1).endswith("-function") and m.group(1) != "module-summary":
                inserts.append((i + 1, m.group(1)))
    for pos, key in sorted(inserts, reverse=True):
        cells.insert(pos, code_cell(f'display(_build_grading_panel("{key}"))'))


def add_summary(cells, exercise_order):
    cells.append(md_cell("## Grades Summary"))
    cells.append(code_cell(f'''_EXERCISE_ORDER = {repr(exercise_order)}

import pandas as _pd
if _os.path.exists(_GRADES_CSV):
    _df = _pd.read_csv(_GRADES_CSV)
    _pivot = _df.pivot(index="student", columns="exercise", values="score")
    _ordered = [ex for ex in _EXERCISE_ORDER if ex in _pivot.columns]
    _extras = [ex for ex in _pivot.columns if ex not in _ordered]
    display(_pivot.reindex(columns=_ordered + _extras))
    print(f"CSV path: {{_os.path.abspath(_GRADES_CSV)}}")
else:
    print("No grades recorded yet.")'''))


def main():
    ap = argparse.ArgumentParser(description="In-place notebook grading patch")
    ap.add_argument("notebook", help="source notebook")
    ap.add_argument("--module-prefix", default=None, help="prefix of the submission files (e.g. module_01)")
    ap.add_argument("--submissions-dir", default=None, help="directory where student submission JSON files are located")
    ap.add_argument("--reference-dir", default="reference_answers", help="directory where reference answer JSON files are located")
    ap.add_argument("--grades-csv", default=None, help="CSV file to store grades")
    args = ap.parse_args()

    src_path = Path(args.notebook)
    if not src_path.exists():
        raise SystemExit(f"Notebook not found: {src_path}")

    ta_path = src_path.with_name(f"{src_path.stem}-TA{src_path.suffix}")
    nb = json.loads(src_path.read_text())

    module_prefix = args.module_prefix or detect_module_prefix(nb)
    if not module_prefix:
        raise SystemExit("Could not detect module_prefix; pass --module-prefix")
    submissions_dir = args.submissions_dir or detect_submissions_dir(nb, module_prefix)
    grades_csv = args.grades_csv or f"grades_{module_prefix}.csv"

    cells = remove_previous_patch(nb["cells"])
    nb["cells"] = cells

    code_demo_to_key = detect_code_demos(nb)
    exercise_order = detect_exercise_order(cells)

    insert_setup_and_nav(cells, module_prefix, submissions_dir, args.reference_dir, grades_csv)
    patch_code_displays(cells, code_demo_to_key)
    add_text_panels(cells)
    add_summary(cells, exercise_order)

    ta_path.write_text(json.dumps(nb, indent=1))
    print(f"Source kept: {src_path}")
    print(f"Patched TA : {ta_path}")
    print("✅ Patch applied successfully. Happy grading! (Hopefully)")


if __name__ == "__main__":
    main()
