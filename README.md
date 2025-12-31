# Flask Web App Starter

A Flask starter template as per [these docs](https://flask.palletsprojects.com/en/3.0.x/quickstart/#a-minimal-application).

## Getting Started

Previews should run automatically when starting a workspace.

## Running locally on Windows

 - Create and activate a virtual environment (PowerShell):

	 ```powershell
	 python -m venv .venv
	 Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned -Force
	 .\.venv\Scripts\Activate.ps1
	 python -m pip install -r requirements.txt
	 ```

 - Start the dev server (PowerShell):

	 ```powershell
	 .\devserver.ps1
	 ```

If you prefer WSL/Git Bash or macOS/Linux, use `devserver.sh` which runs `source .venv/bin/activate` and `python3 -m flask run`.

Direct run (any OS)

- You can also start the app directly with Python:

	```powershell
	python main.py
	```

	This launches the Flask development server on port 8080 (same as `devserver` scripts).