#!/usr/bin/env python3

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import subprocess
import os
import sys
import json

CONFIG_FILE = os.path.expanduser("~/.config/pd2ogg.conf")

BG = "#1a1a2e"
FG = "#d8b4e2"
ACCENT = "#9b59b6"
BUTTON_BG = "#2d1b3d"
BUTTON_FG = "#d8b4e2"
ENTRY_BG = "#2d1b3d"
DONE_COLOR = "#27ae60"

def load_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r") as f:
            return f.read().strip()
    return os.path.expanduser("~/.local/share/Steam/steamapps/common/PAYDAY 2/mods")

def save_config(path):
    os.makedirs(os.path.dirname(CONFIG_FILE), exist_ok=True)
    with open(CONFIG_FILE, "w") as f:
        f.write(path)

def make_short_id(name):
    # deterministic — same name always gives same id
    base = ''.join(c for c in name.lower() if c.isalnum())[:10]
    if not base:
        base = "musicmod"
    # add a short hash of the full name to avoid collisions
    h = str(hash(name.lower()))[-4:]
    return f"{base}{h}"

def convert_file(input_path, mod_folder, short_id):
    ogg_path = os.path.join(mod_folder, "sounds", f"{short_id}.ogg")

    if os.path.exists(ogg_path):
        if not messagebox.askyesno("file exists", f"'{short_id}.ogg' already exists.\nOverwrite?"):
            return None

    result = subprocess.run([
        "ffmpeg", "-i", input_path,
        "-map_metadata", "-1", "-vn",
        "-c:a", "libvorbis", "-b:a", "192k",
        "-ar", "44100", "-ac", "2",
        ogg_path
    ], capture_output=True, text=True)

    if result.returncode != 0:
        err_log = "/tmp/ffmpeg_err.log"
        with open(err_log, "w") as f:
            f.write(result.stderr)
        subprocess.Popen(["xdg-open", err_log])
        messagebox.showerror("error", f"ffmpeg failed.\ncheck {err_log}")
        return None

    return ogg_path

def create_single_mod(input_path, mod_name, music_type, output_dir):
    short_id = make_short_id(mod_name)
    mod_folder = os.path.join(output_dir, mod_name)
    os.makedirs(os.path.join(mod_folder, "sounds"), exist_ok=True)
    os.makedirs(os.path.join(mod_folder, "loc"), exist_ok=True)

    ogg_path = convert_file(input_path, mod_folder, short_id)
    if not ogg_path:
        return None

    if music_type == "MenuMusic":
        loc_content = {
            "menu_jukebox_menu": mod_name,
            "menu_jukebox_screen_menu": mod_name,
            f"menu_jukebox_screen_{short_id}": mod_name
        }

        xml = f'''<table name="{mod_name}">
    <Localization directory="loc" default="en.txt"/>
    <MenuMusic id="{short_id}" source="sounds/{short_id}.ogg"/>
</table>'''
    else:
        loc_content = {
            "menu_jukebox_menu": mod_name,
            "menu_jukebox_screen_menu": mod_name,
            f"menu_jukebox_{short_id}": mod_name,
            f"menu_jukebox_screen_assault": mod_name,
            f"menu_jukebox_screen_stealth": mod_name
        }

        xml = f'''<table name="{mod_name}">
    <Localization directory="loc" default="en.txt"/>
    <HeistMusic id="{short_id}">
        <event name="assault" source="sounds/{short_id}.ogg"/>
        <event name="stealth" start_source="sounds/{short_id}.ogg"/>
    </HeistMusic>
</table>'''

    with open(os.path.join(mod_folder, "loc", "en.txt"), "w") as f:
        f.write(json.dumps(loc_content, indent=4))

    with open(os.path.join(mod_folder, "main.xml"), "w") as f:
        f.write(xml)

    return mod_folder


def create_heist_playlist_mod(phase_data, mod_name, output_dir):
    short_id = make_short_id(mod_name)
    mod_folder = os.path.join(output_dir, mod_name)
    os.makedirs(os.path.join(mod_folder, "sounds"), exist_ok=True)
    os.makedirs(os.path.join(mod_folder, "loc"), exist_ok=True)

    seen_files = {}
    used_track_ids = set()
    event_xml = ""
    loc_content = {
        "menu_jukebox_menu": mod_name,
        "menu_jukebox_screen_menu": mod_name,
        f"menu_jukebox_{short_id}": mod_name
    }

    for i, (phase, filepath) in enumerate(phase_data):
        if filepath in seen_files:
            seen_files[filepath] += 1
            suffix = seen_files[filepath]
            base_id = f"{short_id}_{phase[:3]}_{suffix}"
        else:
            seen_files[filepath] = 1
            base_id = f"{short_id}_{phase[:3]}"

        track_id = base_id
        if track_id in used_track_ids:
            for alt in [f"{short_id}_{phase[:4]}", f"{short_id}_{phase[:5]}", f"{short_id}_{phase}"]:
                if alt not in used_track_ids:
                    track_id = alt
                    break
            else:
                counter = 2
                while f"{base_id}_{counter}" in used_track_ids:
                    counter += 1
                track_id = f"{base_id}_{counter}"

        used_track_ids.add(track_id)

        ogg = convert_file(filepath, mod_folder, track_id)
        if not ogg:
            return None

        event_xml += f'        <event name="{phase}" source="sounds/{track_id}.ogg"/>\n'
        loc_content[f"menu_jukebox_screen_{phase}"] = mod_name

    xml = f'''<table name="{mod_name}">
    <Localization directory="loc" default="en.txt"/>
    <HeistMusic id="{short_id}">
{event_xml}    </HeistMusic>
</table>'''

    with open(os.path.join(mod_folder, "main.xml"), "w") as f:
        f.write(xml)

    with open(os.path.join(mod_folder, "loc", "en.txt"), "w") as f:
        f.write(json.dumps(loc_content, indent=4))

    return mod_folder


def main():
    root = tk.Tk()
    root.title("pd2 music box!")
    root.configure(bg=BG)
    root.geometry("800x720")

    style = ttk.Style()
    style.theme_use("clam")
    style.configure("TLabel", background=BG, foreground=FG, font=("Segoe UI", 10))
    style.configure("TButton", background=BUTTON_BG, foreground=BUTTON_FG, font=("Segoe UI", 10), borderwidth=0)
    style.map("TButton", background=[("active", ACCENT)])
    style.configure("TFrame", background=BG)

    saved_dir = load_config()

    # main scrollable area
    canvas = tk.Canvas(root, bg=BG, highlightthickness=0)
    scrollbar = tk.Scrollbar(root, orient="vertical", command=canvas.yview)
    scroll_frame = tk.Frame(canvas, bg=BG)

    scroll_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
    canvas.create_window((0, 0), window=scroll_frame, anchor="nw")
    canvas.configure(yscrollcommand=scrollbar.set)

    canvas.pack(side="left", fill="both", expand=True)
    scrollbar.pack(side="right", fill="y")

    def _on_mousewheel(event):
        canvas.yview_scroll(int(-1*(event.delta/120)), "units")
    canvas.bind_all("<MouseWheel>", _on_mousewheel)

    frame = tk.Frame(scroll_frame, bg=BG, padx=20, pady=20)
    frame.pack(fill="both", expand=True)

    # title row with reset
    title_row = tk.Frame(frame, bg=BG)
    title_row.pack(fill="x", pady=(0, 5))

    tk.Label(title_row, text="♡ payday 2 music box ♡",
             font=("Segoe UI", 16, "bold"), bg=BG, fg=ACCENT).pack(side="left")

    def restart_app():
        root.destroy()
        subprocess.Popen([sys.executable] + sys.argv)

    tk.Button(title_row, text="↺ reset", font=("Segoe UI", 8), bg="#2d1b3d", fg="#888888",
              relief="flat", padx=8, pady=2, cursor="hand2",
              activebackground="#8e44ad", activeforeground="#ffffff",
              command=restart_app).pack(side="right")

    tk.Label(frame, text="pick a mode and fill in the steps",
             font=("Segoe UI", 9), bg=BG, fg="#888888").pack(pady=(0, 15))

    # vars
    single_input_path = None
    phase_data_internal = {}
    mod_name_var = tk.StringVar()
    music_type_var = tk.StringVar(value="MenuMusic")
    output_dir_var = tk.StringVar(value=saved_dir)
    mode_var = tk.StringVar(value="single")

    step_done = {"1": False, "2": False, "3": False, "4": False, "5": False}
    step_labels = {}

    # --- step 1: mode ---
    step1_frame = tk.Frame(frame, bg=BG, relief="groove", bd=1, highlightbackground=ACCENT, highlightthickness=1)
    step1_frame.pack(fill="x", pady=4)

    step1_header = tk.Frame(step1_frame, bg=step1_frame["bg"])
    step1_header.pack(fill="x", padx=10, pady=(8, 0))

    step1_check = tk.Label(step1_header, text="  ", font=("Segoe UI", 11, "bold"), bg=step1_header["bg"], fg=DONE_COLOR)
    step1_check.pack(side="right")
    step_labels["1"] = step1_check

    tk.Label(step1_header, text="step 1 — what kinda mod?",
             font=("Segoe UI", 11, "bold"), bg=step1_header["bg"], fg=FG).pack(anchor="w")

    mode_frame = tk.Frame(step1_frame, bg=step1_frame["bg"])
    mode_frame.pack(padx=10, pady=(0, 8), fill="x")

    mode_btns = {}
    for val, title, desc in [("single", "single file", "one track, simple"), ("heist", "heist playlist", "different tracks for each phase")]:
        rb_frame = tk.Frame(mode_frame, bg=BUTTON_BG, relief="flat", bd=1, highlightbackground="#3d3d6b", highlightthickness=1, cursor="hand2")
        rb_frame.pack(fill="x", pady=3)

        tk.Label(rb_frame, text=title, font=("Segoe UI", 11, "bold"), bg=BUTTON_BG, fg=BUTTON_FG, cursor="hand2").pack(anchor="w", padx=(15, 10), pady=(6, 0))
        tk.Label(rb_frame, text=desc, font=("Segoe UI", 9), bg=BUTTON_BG, fg="#aaaaaa", cursor="hand2").pack(anchor="w", padx=(15, 10), pady=(0, 6))

        def make_handler(v):
            def h(*_):
                mode_var.set(v)
            return h
        rb_frame.bind("<Button-1>", make_handler(val))
        for c in rb_frame.winfo_children():
            c.bind("<Button-1>", make_handler(val))
        mode_btns[val] = rb_frame

    # --- step 2: files (dynamic) ---
    step2_frame = tk.Frame(frame, bg=BG, relief="groove", bd=1, highlightbackground=ACCENT, highlightthickness=1)
    step2_frame.pack(fill="x", pady=4)

    step2_header = tk.Frame(step2_frame, bg=step2_frame["bg"])
    step2_header.pack(fill="x", padx=10, pady=(8, 0))

    step2_check = tk.Label(step2_header, text="  ", font=("Segoe UI", 11, "bold"), bg=step2_header["bg"], fg=DONE_COLOR)
    step2_check.pack(side="right")
    step_labels["2"] = step2_check

    step2_title = tk.Label(step2_header, text="step 2 — pick your audio files",
                           font=("Segoe UI", 11, "bold"), bg=step2_header["bg"], fg=FG)
    step2_title.pack(anchor="w")

    step2_content = tk.Frame(step2_frame, bg=step2_frame["bg"])
    step2_content.pack(fill="x", padx=10, pady=(5, 8))

    # single file sub-frame
    single_file_frame = tk.Frame(step2_content, bg=step2_content["bg"])

    drop_frame = tk.Frame(single_file_frame, bg="#1f1f3a", relief="solid", bd=2, highlightbackground="#3d3d6b", highlightthickness=1, height=50)
    drop_frame.pack(fill="x", pady=(0, 5))
    drop_frame.pack_propagate(False)

    drop_label = tk.Label(drop_frame, text="♡ drag & drop a file here\n    or click browse (or ctrl+v)",
                          font=("Segoe UI", 9), bg="#1f1f3a", fg="#666666", cursor="hand2")
    drop_label.pack(expand=True)

    for w in [drop_frame, drop_label]:
        w.bind("<Button-1>", lambda e: browse_single())

    single_status = tk.Label(single_file_frame, text="no file selected", font=("Segoe UI", 9), bg=single_file_frame["bg"], fg="#888888")
    single_status.pack(anchor="w")

    tk.Button(single_file_frame, text="browse", command=lambda: browse_single(),
              bg=BUTTON_BG, fg=BUTTON_FG, font=("Segoe UI", 9),
              relief="flat", padx=15, pady=3, cursor="hand2",
              activebackground=ACCENT, activeforeground="#ffffff").pack(anchor="w", pady=(3, 0))

    # heist playlist sub-frame (4x2 grid)
    heist_file_frame = tk.Frame(step2_content, bg=step2_content["bg"])

    tk.Label(heist_file_frame, text="check the phases you want, browse for each:",
             font=("Segoe UI", 9), bg=heist_file_frame["bg"], fg="#aaaaaa").pack(anchor="w", pady=(0, 5))

    HEIST_PHASES_ORDERED = [
        ("stealth", "sneaking around before the alarm"),
        ("suspense_1", "light tension, exploring"),
        ("suspense_2", "moderate tension"),
        ("suspense_3", "high tension, something's brewing"),
        ("anticipation", "building up to assault"),
        ("assault", "guns blazing, combat phase"),
        ("control", "assault winding down"),
        ("suspense_4", "peak tension, critical moment")
    ]

    phase_vars = {}
    phase_path_labels = {}

    grid_frame = tk.Frame(heist_file_frame, bg=heist_file_frame["bg"])
    grid_frame.pack(fill="x")

    for idx, (phase, desc) in enumerate(HEIST_PHASES_ORDERED):
        row = idx // 2
        col = idx % 2

        pf = tk.Frame(grid_frame, bg="#242445", relief="groove", bd=1, highlightbackground="#3d3d6b", highlightthickness=1)
        pf.grid(row=row, column=col, padx=3, pady=3, sticky="nsew")

        grid_frame.columnconfigure(0, weight=1)
        grid_frame.columnconfigure(1, weight=1)

        top_row = tk.Frame(pf, bg="#242445")
        top_row.pack(fill="x", padx=6, pady=(4, 0))

        var = tk.BooleanVar(value=False)
        phase_vars[phase] = var

        cb = tk.Checkbutton(top_row, variable=var, text=phase.replace("_", " ").title(),
                           font=("Segoe UI", 9, "bold"), bg="#242445", fg=FG,
                           selectcolor=BG, activebackground="#242445", activeforeground=FG, cursor="hand2")
        cb.pack(side="left")

        tk.Label(top_row, text=desc, font=("Segoe UI", 7), bg="#242445", fg="#777777").pack(side="left", padx=(6, 0))

        bot_row = tk.Frame(pf, bg="#242445")
        bot_row.pack(fill="x", padx=6, pady=(0, 4))

        lbl = tk.Label(bot_row, text="no file", font=("Segoe UI", 7), bg="#242445", fg="#555555")
        lbl.pack(side="left", fill="x", expand=True)
        phase_path_labels[phase] = lbl

        def make_browse(p):
            def b():
                fp = filedialog.askopenfilename(title=f"pick track for {p}",
                    filetypes=[("audio files", "*.mp3 *.wav *.flac *.ogg *.m4a *.aac *.wma"), ("all files", "*.*")])
                if fp:
                    phase_data_internal[p] = fp
                    phase_path_labels[p].config(text=os.path.basename(fp), fg=FG, font=("Segoe UI", 7, "bold"))
                    phase_vars[p].set(True)
                    update_heist_step2_done()
            return b

        tk.Button(bot_row, text="browse", command=make_browse(phase),
                  bg=BUTTON_BG, fg=BUTTON_FG, font=("Segoe UI", 7),
                  relief="flat", padx=6, pady=1, cursor="hand2",
                  activebackground=ACCENT, activeforeground="#ffffff").pack(side="right")

    def update_heist_step2_done():
        checked = [p for p, v in phase_vars.items() if v.get()]
        if checked:
            step_done["2"] = True
            step_labels["2"].config(text="✓")
        else:
            step_done["2"] = False
            step_labels["2"].config(text="  ")

    def browse_single():
        nonlocal single_input_path
        p = filedialog.askopenfilename(title="pick an audio file",
            filetypes=[("audio files", "*.mp3 *.wav *.flac *.ogg *.m4a *.aac *.wma"), ("all files", "*.*")])
        if p:
            single_input_path = p
            single_status.config(text=os.path.basename(p), fg=FG)
            step_done["2"] = True
            step_labels["2"].config(text="✓")
            default = os.path.splitext(os.path.basename(p))[0]
            mod_name_var.set(default)

    root.bind("<Control-v>", lambda e: paste_files())

    def paste_files():
        try:
            clip = root.clipboard_get()
            lines = clip.strip().split('\n')
            valid = [l.strip().strip("'\"").strip() for l in lines if os.path.exists(l.strip().strip("'\"").strip()) and os.path.isfile(l.strip().strip("'\"").strip())]
            if valid and mode_var.get() == "single":
                single_input_path = valid[0]
                single_status.config(text=os.path.basename(valid[0]), fg=FG)
                step_done["2"] = True
                step_labels["2"].config(text="✓")
                default = os.path.splitext(os.path.basename(valid[0]))[0]
                mod_name_var.set(default)
        except:
            pass

    def update_step2_ui():
        if mode_var.get() == "heist":
            single_file_frame.pack_forget()
            heist_file_frame.pack(fill="both", expand=True)
            step2_title.config(text="step 2 — pick tracks for each phase")
            single_status.config(text="no file selected", fg="#888888")
        else:
            heist_file_frame.pack_forget()
            single_file_frame.pack(fill="x")
            step2_title.config(text="step 2 — pick your audio file")

    mode_var.trace_add("write", lambda *_: update_step2_ui())

    def update_mode_colors():
        for val, fw in mode_btns.items():
            if mode_var.get() == val:
                fw.config(bg=ACCENT)
                for c in fw.winfo_children():
                    try: c.config(bg=ACCENT)
                    except: pass
                    try:
                        if 'bold' in (c.cget('font') or ''):
                            c.config(fg="#ffffff")
                        else:
                            c.config(fg="#dddddd")
                    except: pass
                if val == "heist":
                    music_type_var.set("HeistMusic")
                else:
                    music_type_var.set("MenuMusic")
                step_done["1"] = True
                step_labels["1"].config(text="✓")
            else:
                fw.config(bg=BUTTON_BG)
                for c in fw.winfo_children():
                    try: c.config(bg=BUTTON_BG)
                    except: pass
                    try:
                        if 'bold' in (c.cget('font') or ''):
                            c.config(fg=BUTTON_FG)
                        else:
                            c.config(fg="#aaaaaa")
                    except: pass

    mode_var.trace_add("write", lambda *_: update_mode_colors())
    update_mode_colors()
    update_step2_ui()

    # --- step 3: name ---
    step3_frame = tk.Frame(frame, bg=BG, relief="groove", bd=1, highlightbackground=ACCENT, highlightthickness=1)
    step3_frame.pack(fill="x", pady=4)

    step3_header = tk.Frame(step3_frame, bg=step3_frame["bg"])
    step3_header.pack(fill="x", padx=10, pady=(8, 0))

    step3_check = tk.Label(step3_header, text="  ", font=("Segoe UI", 11, "bold"), bg=step3_header["bg"], fg=DONE_COLOR)
    step3_check.pack(side="right")
    step_labels["3"] = step3_check

    tk.Label(step3_header, text="step 3 — name your mod",
             font=("Segoe UI", 11, "bold"), bg=step3_header["bg"], fg=FG).pack(anchor="w")

    placeholder_text = "e.g. Hotline Miami 2 - Menu Music"
    is_placeholder = [True]

    name_entry = tk.Entry(step3_frame, font=("Segoe UI", 10), bg=ENTRY_BG, fg="#555555",
                          insertbackground=FG, relief="flat", bd=5)
    name_entry.insert(0, placeholder_text)
    name_entry.pack(fill="x", padx=10, pady=(0, 8))

    def on_focus_in(e):
        if is_placeholder[0]:
            name_entry.delete(0, "end")
            name_entry.config(fg=FG)
            is_placeholder[0] = False

    def on_focus_out(e):
        if not name_entry.get().strip():
            name_entry.insert(0, placeholder_text)
            name_entry.config(fg="#555555")
            is_placeholder[0] = True
            step_done["3"] = False
            step_labels["3"].config(text="  ")

    def on_key(e):
        if is_placeholder[0]:
            name_entry.delete(0, "end")
            name_entry.config(fg=FG)
            is_placeholder[0] = False
        if name_entry.get().strip() and name_entry.get().strip() != placeholder_text:
            step_done["3"] = True
            step_labels["3"].config(text="✓")
        else:
            step_done["3"] = False
            step_labels["3"].config(text="  ")

    name_entry.bind("<FocusIn>", on_focus_in)
    name_entry.bind("<FocusOut>", on_focus_out)
    name_entry.bind("<KeyRelease>", on_key)

    # --- step 4: type ---
    step4_frame = tk.Frame(frame, bg=BG, relief="groove", bd=1, highlightbackground=ACCENT, highlightthickness=1)
    step4_frame.pack(fill="x", pady=4)

    step4_header = tk.Frame(step4_frame, bg=step4_frame["bg"])
    step4_header.pack(fill="x", padx=10, pady=(8, 0))

    step4_check = tk.Label(step4_header, text="  ", font=("Segoe UI", 11, "bold"), bg=step4_header["bg"], fg=DONE_COLOR)
    step4_check.pack(side="right")
    step_labels["4"] = step4_check

    tk.Label(step4_header, text="step 4 — what kind of music?",
             font=("Segoe UI", 11, "bold"), bg=step4_header["bg"], fg=FG).pack(anchor="w")

    type_frame_inner = tk.Frame(step4_frame, bg=step4_frame["bg"])
    type_frame_inner.pack(padx=10, pady=(0, 8))

    menu_rb = tk.Radiobutton(type_frame_inner, text="menu music (background track)",
                              variable=music_type_var, value="MenuMusic",
                              bg=step4_frame["bg"], fg=FG, selectcolor=BG,
                              activebackground=step4_frame["bg"], activeforeground=FG,
                              font=("Segoe UI", 9), indicatoron=0,
                              width=25, relief="flat", padx=5, pady=2, cursor="hand2")
    menu_rb.pack(side="left", padx=(0, 10))

    heist_rb = tk.Radiobutton(type_frame_inner, text="heist music (assault/stealth)",
                               variable=music_type_var, value="HeistMusic",
                               bg=step4_frame["bg"], fg=FG, selectcolor=BG,
                               activebackground=step4_frame["bg"], activeforeground=FG,
                               font=("Segoe UI", 9), indicatoron=0,
                               width=25, relief="flat", padx=5, pady=2, cursor="hand2")
    heist_rb.pack(side="left")

    def update_type_colors():
        for rb, val in [(menu_rb, "MenuMusic"), (heist_rb, "HeistMusic")]:
            if music_type_var.get() == val:
                rb.config(bg=ACCENT, fg="#ffffff")
                step_labels["4"].config(text="✓")
                step_done["4"] = True
            else:
                rb.config(bg=BUTTON_BG, fg=BUTTON_FG)

    music_type_var.trace_add("write", lambda *_: update_type_colors())
    update_type_colors()

    # --- step 5: output ---
    step5_frame = tk.Frame(frame, bg=BG, relief="groove", bd=1, highlightbackground=ACCENT, highlightthickness=1)
    step5_frame.pack(fill="x", pady=4)

    step5_header = tk.Frame(step5_frame, bg=step5_frame["bg"])
    step5_header.pack(fill="x", padx=10, pady=(8, 0))

    step5_check = tk.Label(step5_header, text="  ", font=("Segoe UI", 11, "bold"), bg=step5_header["bg"], fg=DONE_COLOR)
    step5_check.pack(side="right")
    step_labels["5"] = step5_check

    tk.Label(step5_header, text="step 5 — where to save it",
             font=("Segoe UI", 11, "bold"), bg=step5_header["bg"], fg=FG).pack(anchor="w")

    dir_label = tk.Label(step5_frame, textvariable=output_dir_var,
                         font=("Segoe UI", 8), bg=step5_frame["bg"], fg="#aaaaaa", wraplength=400)
    dir_label.pack(anchor="w", padx=10)

    def pick_output():
        d = filedialog.askdirectory(title="where to save?", initialdir=output_dir_var.get())
        if d:
            output_dir_var.set(d)
            save_config(d)
            step_done["5"] = True
            step_labels["5"].config(text="✓")

    tk.Button(step5_frame, text="choose folder", command=pick_output,
              bg=BUTTON_BG, fg=BUTTON_FG, font=("Segoe UI", 9),
              relief="flat", padx=15, pady=3, cursor="hand2",
              activebackground=ACCENT, activeforeground="#ffffff").pack(padx=10, pady=(2, 8), anchor="w")

    # --- go ---
    def do_the_thing():
        name = name_entry.get().strip()
        if is_placeholder[0] or name == placeholder_text or not name:
            messagebox.showerror("error", "name yo mod")
            return

        out = output_dir_var.get()
        mode = mode_var.get()

        if mode == "heist":
            selected = [(p, phase_data_internal[p]) for p in phase_vars if phase_vars[p].get() and p in phase_data_internal]
            if not selected:
                messagebox.showerror("error", "pick at least one phase and assign a file")
                return
            result = create_heist_playlist_mod(selected, name, out)
        else:
            if not single_input_path:
                messagebox.showerror("error", "pick a file first lol")
                return
            result = create_single_mod(single_input_path, name, music_type_var.get(), out)

        if result:
            what_now = tk.Toplevel(root)
            what_now.title("done!")
            what_now.configure(bg=BG)
            what_now.geometry("450x350")
            what_now.resizable(False, False)

            tk.Label(what_now, text="♡ mod created! ♡",
                     font=("Segoe UI", 16, "bold"), bg=BG, fg=ACCENT).pack(pady=(20, 10))

            tk.Label(what_now, text="your mod is at:", font=("Segoe UI", 10), bg=BG, fg=FG).pack()

            pf = tk.Frame(what_now, bg="#242445", relief="solid", bd=1)
            pf.pack(padx=20, pady=5, fill="x")
            tk.Label(pf, text=result, font=("Segoe UI", 8), bg="#242445", fg="#aaaaaa", wraplength=380).pack(padx=10, pady=8)

            tk.Label(what_now, text="\nnext steps:", font=("Segoe UI", 11, "bold"), bg=BG, fg=FG).pack()

            sf = tk.Frame(what_now, bg=BG)
            sf.pack(padx=30, pady=5, anchor="w")
            for s in ["1. restart payday 2", "2. go to options → jukebox", "3. find your mod in the list", "4. select it and enjoy!"]:
                tk.Label(sf, text=s, font=("Segoe UI", 10), bg=BG, fg=FG, anchor="w").pack(fill="x", pady=2)

            tk.Button(what_now, text="got it!", command=what_now.destroy,
                      bg=ACCENT, fg="#ffffff", font=("Segoe UI", 10, "bold"),
                      relief="flat", padx=20, pady=5, cursor="hand2",
                      activebackground="#8e44ad", activeforeground="#ffffff").pack(pady=(15, 10))

            what_now.transient(root)
            what_now.grab_set()

    tk.Button(frame, text="✦ create mod ✦", command=do_the_thing,
              bg=ACCENT, fg="#ffffff", font=("Segoe UI", 12, "bold"),
              relief="flat", padx=30, pady=8, cursor="hand2",
              activebackground="#8e44ad", activeforeground="#ffffff").pack(pady=(15, 5))

    tk.Label(frame, text="requires: beardlib + project cell beta",
             font=("Segoe UI", 8), bg=BG, fg="#666666").pack()
    tk.Label(frame, text="made with ♡ for the payday 2 modding community",
             font=("Segoe UI", 8), bg=BG, fg="#444444").pack()

    root.mainloop()

if __name__ == "__main__":
    main()
