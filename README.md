# SuperRegistrationMachine

A cross-platform Streamlit app to drill your timing for course registration. Practice the last seconds before 7:00:00 AM, capture reaction times separately for millisecond and standard views, and keep looping automatically.

## Quick install (macOS/Linux)
```bash
git clone https://github.com/<your-username>/SuperRegistrationMachine.git
cd SuperRegistrationMachine
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

## Quick install (Windows PowerShell)
```powershell
git clone https://github.com/<your-username>/SuperRegistrationMachine.git
cd SuperRegistrationMachine
py -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
streamlit run app.py
```

## Using the app
- Pick how many seconds before 7:00:00 the timer starts (2–30s).
- Toggle milliseconds on/off; stats track each mode separately.
- Click **REGISTER** right after 7:00:00; your run auto-resets after ~3s.
