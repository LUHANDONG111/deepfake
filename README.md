# Deepfake Video Detection Web System

Flask + SQLite single-machine web application for visual deepfake video detection.

## Setup

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python app.py
```

Open http://127.0.0.1:5000.

The first implementation includes real OpenCV-based face localization and alignment.
The Xception classifier is exposed through a replaceable classifier interface; place
future model-loading code in `inference/classifier.py` without changing the API or UI.
