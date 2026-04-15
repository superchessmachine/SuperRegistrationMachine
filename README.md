# Autoregister helper (use at your own risk)
If you really want to automate a registration click, copy the code from `autoregister.js` and run it in your browser console on the enrollment page—use it at your own risk.
1. Navigate to the registration page and make sure the button you normally click is visible.
2. Open the browser console (Cmd+Option+J on macOS, Ctrl+Shift+J on Windows).
3. Paste the entire `autoregister.js` snippet and press Enter.
4. Enter the exact 24h target time (`HH:MM:SS.mmm`) and any extra delay when prompted; the script schedules a click on `ctl00_contentPlaceHolder_ibEnroll`.
5. Leave the tab focused; the script logs its countdown and clicks when the time + delay expires.

# SuperRegistrationMachine

A cross-platform Streamlit app to drill your timing for course registration. Practice the last seconds before 7:00:00 AM, tune the timer from 0-5 decimal places, benchmark two settings side-by-side, and keep looping automatically.

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
- Choose 0–5 decimal places for the timer display.
- Click **REGISTER** right after 7:00:00; your run auto-resets after ~3s.
- Use the **Benchmark** tab to compare two settings over 5 successful samples each and view error-bar charts.
