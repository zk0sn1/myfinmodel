# Streamlit PC Deployment Setup Spec (Double-Click Launcher + Installer)

This document defines a practical, repeatable deployment workflow for **Blockish/myfinmodel** that keeps the existing Streamlit app and packages it for Windows PCs with a double-click launch experience.

It includes both:

- **Option A (Portable ZIP)**: no installer, easy internal sharing
- **Option B (Installer EXE)**: polished setup/uninstall using Inno Setup

---

## 1) Goals and constraints

- Keep the current **Streamlit app architecture** (no UI rewrite).
- Users should launch by **double-click** (no terminal required).
- No public hosting; app runs locally on each PC (`localhost`).
- Package in a repeatable way for versioned releases.

---

## 2) Current repo assumptions

Based on current scaffolding:

- Entrypoint: `app.py` (Streamlit)
- Dependencies include `streamlit`, `plotly`, `pandas`, `numpy`, etc.
- Charts are rendered in Streamlit and open in browser.

---

## 3) Runtime behavior design

Double-click launcher should:

1. Start the packaged Streamlit runtime in the background.
2. Open default browser to local URL (for example `http://localhost:8501`).
3. Keep process running until user closes app/browser.

Recommended Streamlit launch flags:

- `--server.headless true`
- `--browser.gatherUsageStats false`
- `--server.port 8501` (or fallback if occupied)

---

## 4) File layout to add in repo

Create a packaging folder:

```text
packaging/
  launch_streamlit.py
  launch_myfinmodel.bat
  myfinmodel.spec
  inno/
    MyFinModel.iss
```

- `launch_streamlit.py`: Python launcher script (starts Streamlit and opens browser)
- `launch_myfinmodel.bat`: user-facing double-click entry for portable mode
- `myfinmodel.spec`: optional PyInstaller spec for reproducible build config
- `inno/MyFinModel.iss`: installer definition

---

## 5) Launcher implementation spec

### 5.1 `packaging/launch_streamlit.py`

Behavior requirements:

- Detect bundled vs development mode (`sys._MEIPASS` handling if needed).
- Resolve absolute path to `app.py`.
- Start Streamlit via:
  - `python -m streamlit run <app.py> ...` in dev, or
  - packaged executable runtime in built mode.
- Wait briefly (1–3s) then open browser with `webbrowser.open(url)`.
- Gracefully handle:
  - missing `app.py`
  - occupied port
  - failed subprocess start
- Write minimal log file in `%LOCALAPPDATA%/MyFinModel/logs`.

### 5.2 `packaging/launch_myfinmodel.bat`

Behavior requirements:

- Double-clickable by non-technical users.
- Launches bundled executable (or launcher script) without terminal noise.
- Optional: set window title and user-friendly error message if launch fails.

Example logic:

```bat
@echo off
setlocal
cd /d "%~dp0"
start "" "MyFinModelLauncher.exe"
```

(Exact target name depends on PyInstaller output name.)

---

## 6) Build environment spec (Windows)

Use a clean Windows build machine matching target architecture (x64).

### 6.1 Create build venv

```powershell
python -m venv .venv-build
.\.venv-build\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
pip install pyinstaller
```

### 6.2 Verify app before packaging

```powershell
streamlit run app.py
```

Confirm UI loads and charts render.

---

## 7) PyInstaller packaging spec

Two patterns supported:

### 7.1 One-folder build (recommended)

Use **onedir** because Streamlit has many dynamic assets.

```powershell
pyinstaller --noconfirm --clean --onedir --name MyFinModelLauncher packaging\launch_streamlit.py
```

### 7.2 One-file build (optional, higher risk)

```powershell
pyinstaller --noconfirm --clean --onefile --name MyFinModelLauncher packaging\launch_streamlit.py
```

If onefile has runtime issues, revert to onedir.

### 7.3 Hidden imports / data

If runtime errors occur, include hidden imports for Streamlit/Plotly modules and bundle static/data assets used by app.

---

## 8) Option A: Portable ZIP distribution

### 8.1 Package contents

Create release folder containing:

```text
MyFinModel/
  MyFinModelLauncher.exe      (or launcher script + python runtime strategy)
  launch_myfinmodel.bat
  _internal/                  (PyInstaller onedir payload)
  VERSION.txt
  README-Run.txt
```

### 8.2 End-user steps

1. Unzip folder to any writable location.
2. Double-click `launch_myfinmodel.bat` (or `MyFinModelLauncher.exe`).
3. Browser opens automatically to local app.

### 8.3 Portable pros/cons

- Pros: fastest distribution, easy internal testing
- Cons: no Start Menu entry, no uninstall registry entry

---

## 9) Option B: Installer EXE (Inno Setup)

### 9.1 Prerequisite

Install Inno Setup on build machine.

### 9.2 Inno script requirements (`packaging/inno/MyFinModel.iss`)

Installer should:

- Install to `C:\Program Files\MyFinModel` (default)
- Copy all onedir build files
- Create:
  - Start Menu shortcut
  - optional Desktop shortcut
- Register uninstall entry
- Optionally launch app after install

### 9.3 Build installer

Compile `.iss` in Inno Setup to output:

```text
dist-installer/MyFinModel-Setup-<version>.exe
```

### 9.4 Installer pros/cons

- Pros: professional install/uninstall, easier for broad rollout
- Cons: extra build step

---

## 10) Localhost testing strategy

Testing remains local (no web server deployment required).

### 10.1 Test matrix

- Fresh machine with no Python installed
- Standard user (non-admin) launch
- Different default browsers
- Port already in use (8501)
- First-run startup timing
- Chart rendering/export behavior

### 10.2 Acceptance criteria

- App launches by double-click with no terminal interaction required
- Browser opens automatically
- Core simulation and chart tabs function correctly
- App closes cleanly and relaunches successfully

---

## 11) Versioning and release process

For each release:

1. Update `VERSION.txt` (e.g., `v0.2.0`).
2. Build on clean Windows env.
3. Smoke test portable package.
4. Build installer.
5. Publish artifacts:
   - `MyFinModel-vX.Y.Z-portable.zip`
   - `MyFinModel-Setup-vX.Y.Z.exe`
6. Attach release notes (features/fixes/known issues).

---

## 12) Security and operational notes

- Some antivirus products may flag unsigned executables.
- For wider distribution, consider code-signing certificate.
- Do not bundle secrets/API keys in package.
- Keep logs free of sensitive financial inputs unless explicitly needed.

---

## 13) Recommended immediate implementation plan

1. Add `packaging/launch_streamlit.py` and test local launcher behavior.
2. Add PyInstaller build command to a script (e.g., `scripts/build_windows.ps1`).
3. Produce **portable ZIP** first and validate with users.
4. Add Inno Setup script and produce installer once portable flow is stable.
5. Document end-user instructions in `README-Run.txt`.

---

## 14) Quick command checklist

```powershell
# from repo root
python -m venv .venv-build
.\.venv-build\Scripts\Activate.ps1
pip install -r requirements.txt
pip install pyinstaller

# sanity run
streamlit run app.py

# package
pyinstaller --noconfirm --clean --onedir --name MyFinModelLauncher packaging\launch_streamlit.py
```

---

## 15) Future enhancements (optional)

- Automatic port fallback detection and display to user.
- Lightweight system tray indicator for running status.
- Auto-update mechanism (internal update feed).
- Crash reporter and diagnostics bundle export.

---

This spec is intentionally implementation-ready while preserving your current Streamlit architecture and enabling both portable and installer-based Windows deployment.
