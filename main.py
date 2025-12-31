from app import create_app

app = create_app()


if __name__ == "__main__":
	# Allow running the app directly: `python main.py`
	# Matches the devserver default port used elsewhere (8080)
	app.run(host="0.0.0.0", port=8080)
