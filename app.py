import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional

import altair as alt
import numpy as np
import pandas as pd
import streamlit as st
import streamlit.components.v1 as components


APP_NAME = "SuperRegistrationMachine"
DEFAULT_WINDOW_SECONDS = 10.0  # default: from 6:59:50 to 7:00:00
RESET_DELAY = 3.0  # auto-restart delay after clicking
TARGET_TIME = datetime(2000, 1, 1, 7, 0, 0)  # purely display, not real clock
RESULT_DIGITS = 5
BENCHMARK_SAMPLES = 5
PRECISION_OPTIONS = [0, 1, 2, 3, 4, 5]


def precision_label(digits: int) -> str:
    return f"{digits} decimal place{'s' if digits != 1 else ''}"


def setting_label(precision_digits: int, window_seconds: float) -> str:
    return f"{precision_digits} dp • {window_seconds:.1f}s lead"


def get_base_time(window_seconds: float) -> datetime:
    return TARGET_TIME - timedelta(seconds=window_seconds)


def format_clock(elapsed: float, show_millis: bool, window_seconds: float) -> str:
    base = get_base_time(window_seconds) + timedelta(seconds=max(0.0, elapsed))
    # allow flexible fractional precision
    digits = st.session_state.get("precision_digits", 3 if show_millis else 2)
    digits = max(0, min(5, int(digits)))
    if digits == 0:
        return base.strftime("%I:%M:%S %p").lstrip("0")
    raw = base.strftime("%I:%M:%S.%f %p").lstrip("0")
    time_part, meridiem = raw.split(" ")
    trimmed = time_part[:- (6 - digits)]  # drop extra microsecond digits
    return f"{trimmed} {meridiem}"


def format_remaining(seconds: float, show_millis: bool, *, digits_override: Optional[int] = None) -> str:
    total = max(0.0, seconds)
    h = int(total // 3600)
    m = int((total % 3600) // 60)
    s = total % 60
    base_digits = st.session_state.get("precision_digits", 3 if show_millis else 2)
    digits = digits_override if digits_override is not None else base_digits
    digits = max(0, min(5, int(digits)))
    frac_fmt = f"{s:0{3 + digits}.{digits}f}" if digits else f"{int(s):02d}"
    return f"{h:02d}:{m:02d}:{frac_fmt}"


def init_state() -> None:
    defaults = {
        "round_started_at": time.time(),
        "last_result": None,
        "last_status": None,
        "next_reset_at": None,
        "window_seconds": DEFAULT_WINDOW_SECONDS,
        "precision_digits": 3,
        "attempt_history": [],
        "benchmark_active": False,
        "benchmark_settings": [],
        "benchmark_samples": [],
        "benchmark_current_index": 0,
        "benchmark_run_id": 0,
        "benchmark_notice": None,
        "benchmark_notice_status": None,
        "benchmark_a_precision_digits": 2,
        "benchmark_a_window_seconds": DEFAULT_WINDOW_SECONDS,
        "benchmark_b_precision_digits": 3,
        "benchmark_b_window_seconds": DEFAULT_WINDOW_SECONDS,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def update_current_setting(precision_digits: int, window_seconds: float, *, reset_round: bool) -> None:
    st.session_state.precision_digits = int(precision_digits)
    st.session_state.window_seconds = float(window_seconds)
    if reset_round:
        reset_attempt()


def benchmark_counts() -> Dict[str, int]:
    counts: Dict[str, int] = {}
    current_run_id = st.session_state.get("benchmark_run_id", 0)
    for sample in st.session_state.get("benchmark_samples", []):
        if sample.get("run_id") != current_run_id:
            continue
        setting_id = str(sample["setting_id"])
        counts[setting_id] = counts.get(setting_id, 0) + 1
    return counts


def current_benchmark_setting() -> Optional[Dict[str, float | int | str]]:
    if not st.session_state.get("benchmark_active"):
        return None
    settings = st.session_state.get("benchmark_settings", [])
    current_index = int(st.session_state.get("benchmark_current_index", 0))
    if current_index >= len(settings):
        return None
    return settings[current_index]


def build_benchmark_settings() -> List[Dict[str, float | int | str]]:
    return [
        {
            "id": "A",
            "name": "Setting A",
            "precision_digits": int(st.session_state.get("benchmark_a_precision_digits", 2)),
            "window_seconds": float(st.session_state.get("benchmark_a_window_seconds", DEFAULT_WINDOW_SECONDS)),
        },
        {
            "id": "B",
            "name": "Setting B",
            "precision_digits": int(st.session_state.get("benchmark_b_precision_digits", 3)),
            "window_seconds": float(st.session_state.get("benchmark_b_window_seconds", DEFAULT_WINDOW_SECONDS)),
        },
    ]


def start_benchmark() -> None:
    settings = build_benchmark_settings()
    first, second = settings
    if (
        first["precision_digits"] == second["precision_digits"]
        and first["window_seconds"] == second["window_seconds"]
    ):
        st.session_state.benchmark_notice_status = "warning"
        st.session_state.benchmark_notice = "Pick two different settings before starting a benchmark."
        return

    st.session_state.benchmark_run_id = int(st.session_state.get("benchmark_run_id", 0)) + 1
    st.session_state.benchmark_settings = settings
    st.session_state.benchmark_samples = []
    st.session_state.benchmark_current_index = 0
    st.session_state.benchmark_active = True
    st.session_state.benchmark_notice_status = "success"
    st.session_state.benchmark_notice = "Benchmark started. Use the Countdown tab to collect samples."
    st.session_state.last_status = None
    st.session_state.last_result = None
    st.session_state.next_reset_at = None

    update_current_setting(
        int(first["precision_digits"]),
        float(first["window_seconds"]),
        reset_round=True,
    )


def stop_benchmark() -> None:
    st.session_state.benchmark_active = False
    st.session_state.benchmark_current_index = 0
    st.session_state.benchmark_notice_status = "warning"
    st.session_state.benchmark_notice = "Benchmark stopped before completion."


def record_attempt(
    reaction: float,
    precision_digits: int,
    window_seconds: float,
    *,
    benchmark_setting_id: Optional[str] = None,
    benchmark_setting_name: Optional[str] = None,
) -> None:
    st.session_state.attempt_history.append(
        {
            "attempt_number": len(st.session_state.attempt_history) + 1,
            "reaction_s": float(reaction),
            "precision_digits": int(precision_digits),
            "window_seconds": float(window_seconds),
            "setting": setting_label(precision_digits, window_seconds),
            "benchmark_setting_id": benchmark_setting_id,
            "benchmark_setting_name": benchmark_setting_name,
        }
    )


def maybe_record_benchmark_sample(
    reaction: float,
    precision_digits: int,
    window_seconds: float,
) -> str:
    setting = current_benchmark_setting()
    if not setting:
        return ""

    counts = benchmark_counts()
    setting_id = str(setting["id"])
    sample_number = counts.get(setting_id, 0) + 1

    st.session_state.benchmark_samples.append(
        {
            "run_id": int(st.session_state.get("benchmark_run_id", 0)),
            "setting_id": setting_id,
            "setting_name": str(setting["name"]),
            "setting_label": setting_label(precision_digits, window_seconds),
            "precision_digits": int(precision_digits),
            "window_seconds": float(window_seconds),
            "sample_number": sample_number,
            "reaction_s": float(reaction),
        }
    )

    if sample_number < BENCHMARK_SAMPLES:
        return f" Benchmark {setting['name']}: sample {sample_number}/{BENCHMARK_SAMPLES}."

    next_index = int(st.session_state.get("benchmark_current_index", 0)) + 1
    if next_index < len(st.session_state.get("benchmark_settings", [])):
        st.session_state.benchmark_current_index = next_index
        next_setting = st.session_state.benchmark_settings[next_index]
        update_current_setting(
            int(next_setting["precision_digits"]),
            float(next_setting["window_seconds"]),
            reset_round=False,
        )
        return (
            f" Benchmark {setting['name']} complete. "
            f"Next: {setting_label(int(next_setting['precision_digits']), float(next_setting['window_seconds']))}."
        )

    st.session_state.benchmark_active = False
    st.session_state.benchmark_current_index = 0
    st.session_state.benchmark_notice_status = "success"
    st.session_state.benchmark_notice = "Benchmark complete. Review the comparison charts below."
    return " Benchmark complete. Open the Benchmark tab for comparison charts."


def benchmark_summary_frame() -> Optional[pd.DataFrame]:
    samples = st.session_state.get("benchmark_samples", [])
    if not samples:
        return None

    data = pd.DataFrame(samples)
    current_run_id = int(st.session_state.get("benchmark_run_id", 0))
    data = data[data["run_id"] == current_run_id]
    if data.empty:
        return None

    summary = (
        data.groupby(["setting_id", "setting_name", "setting_label"], as_index=False)
        .agg(
            samples=("reaction_s", "count"),
            mean_s=("reaction_s", "mean"),
            std_s=("reaction_s", lambda values: float(np.std(values, ddof=1)) if len(values) > 1 else 0.0),
            best_s=("reaction_s", "min"),
        )
        .sort_values("setting_id")
    )
    summary["sem_s"] = summary.apply(
        lambda row: row["std_s"] / np.sqrt(row["samples"]) if row["samples"] > 1 else 0.0,
        axis=1,
    )
    summary["error_low"] = summary["mean_s"] - summary["sem_s"]
    summary["error_high"] = summary["mean_s"] + summary["sem_s"]
    return summary


def reset_attempt() -> None:
    st.session_state.round_started_at = time.time()
    st.session_state.last_result = None
    st.session_state.last_status = None
    st.session_state.next_reset_at = None


def elapsed_seconds() -> float:
    return max(0.0, time.time() - st.session_state.round_started_at)


def register_click() -> None:
    elapsed = elapsed_seconds()
    window_seconds = float(st.session_state.get("window_seconds", DEFAULT_WINDOW_SECONDS))
    precision_digits = int(st.session_state.get("precision_digits", 3))
    show_ms = precision_digits > 0
    if elapsed < window_seconds:
        remaining = window_seconds - elapsed
        st.session_state.last_status = "warning"
        st.session_state.last_result = (
            f"Too early! {format_remaining(remaining, show_ms, digits_override=RESULT_DIGITS)} "
            "remain before 7:00:00."
        )
    else:
        reaction = elapsed - window_seconds
        benchmark_setting = current_benchmark_setting()
        benchmark_setting_id = str(benchmark_setting["id"]) if benchmark_setting else None
        benchmark_setting_name = str(benchmark_setting["name"]) if benchmark_setting else None
        record_attempt(
            reaction,
            precision_digits,
            window_seconds,
            benchmark_setting_id=benchmark_setting_id,
            benchmark_setting_name=benchmark_setting_name,
        )
        st.session_state.last_status = "success"
        st.session_state.last_result = (
            f"Registered {reaction:.5f}s after 7:00:00. Nice reflexes!"
            f"{maybe_record_benchmark_sample(reaction, precision_digits, window_seconds)}"
        )
    st.session_state.next_reset_at = time.time() + RESET_DELAY


def maybe_auto_reset() -> None:
    if st.session_state.next_reset_at:
        remaining = st.session_state.next_reset_at - time.time()
        if remaining <= 0:
            reset_attempt()
            st.experimental_rerun()
        else:
            # poll the timer by asking the client to request a rerun
            interval_ms = max(300, int(min(remaining, 1.0) * 1000))
            components.html(
                f"<script>setTimeout(() => window.parent.postMessage({{isStreamlitMessage:true, type:'streamlit:requestRerun'}}, '*'), {interval_ms});</script>",
                height=0,
                width=0,
            )


def cool_styles() -> None:
    st.markdown(
        """
        <style>
        .main {
            background: radial-gradient(circle at 20% 20%, #0f172a 0, #020617 35%, #000 70%);
            color: #e2e8f0;
            font-family: 'Inter', system-ui, -apple-system, sans-serif;
        }
        div.stButton > button {
            border-radius: 999px;
            padding: 0.75rem 1.35rem;
            border: 1px solid #38bdf8;
            background: linear-gradient(90deg, #06b6d4, #2563eb);
            color: #0b1220;
            font-weight: 700;
            letter-spacing: 0.02em;
        }
        div.stTab { margin-top: 0.5rem; }
        .countdown-box {
            padding: 1.2rem 1.6rem;
            border-radius: 20px;
            background: linear-gradient(135deg, rgba(56, 189, 248, 0.12), rgba(94, 234, 212, 0.08));
            border: 1px solid rgba(148, 163, 184, 0.3);
        }
        .clock-face {
            font-size: 4rem;
            font-variant-numeric: tabular-nums;
            font-weight: 800;
            text-align: center;
            color: #e0f2fe;
            text-shadow: 0 8px 24px rgba(0, 0, 0, 0.4);
        }
        .ready {
            color: #34d399;
            text-shadow: 0 0 22px rgba(52, 211, 153, 0.75);
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def countdown_card() -> None:
    benchmark_active = bool(st.session_state.get("benchmark_active", False))
    current_setting = current_benchmark_setting()
    if benchmark_active and current_setting:
        counts = benchmark_counts()
        current_count = counts.get(str(current_setting["id"]), 0)
        st.info(
            "Benchmark in progress — "
            f"{current_setting['name']} sample {current_count + 1}/{BENCHMARK_SAMPLES} • "
            f"{setting_label(int(current_setting['precision_digits']), float(current_setting['window_seconds']))}"
        )

    precision = st.select_slider(
        "Timer precision (decimal places)",
        options=PRECISION_OPTIONS,
        value=int(st.session_state.get("precision_digits", 3)),
        key="precision_digits",
        help="Choose how many decimal digits the timer displays.",
        disabled=benchmark_active,
    )
    show_ms = precision > 0
    default_window = float(st.session_state.get("window_seconds", DEFAULT_WINDOW_SECONDS))
    window_seconds = st.slider(
        "Seconds before 7:00:00 to start",
        min_value=2.0,
        max_value=30.0,
        value=default_window,
        step=0.5,
        key="window_seconds",
        on_change=reset_attempt,
        help="Adjust how far before 7:00:00 the countdown begins.",
        disabled=benchmark_active,
    )
    base_time = get_base_time(window_seconds)
    elapsed = elapsed_seconds()
    remaining = window_seconds - elapsed
    ready = remaining <= 0.0
    display_time = format_clock(elapsed, show_ms, window_seconds)

    components.html(
        f"""
        <style>
        .trainer-box {{
            padding: 1.2rem 1.6rem;
            border-radius: 20px;
            background: linear-gradient(135deg, rgba(56, 189, 248, 0.12), rgba(94, 234, 212, 0.08));
            border: 1px solid rgba(148, 163, 184, 0.3);
        }}
        .trainer-clock {{
            font-size: 4rem;
            font-variant-numeric: tabular-nums;
            font-weight: 800;
            text-align: center;
            color: #e0f2fe;
            text-shadow: 0 8px 24px rgba(0, 0, 0, 0.4);
            transition: color 0.3s ease, text-shadow 0.3s ease;
        }}
        .trainer-ready {{
            color: #34d399;
            text-shadow: 0 0 22px rgba(52, 211, 153, 0.75);
        }}
        </style>
        <div class="trainer-box">
            <div style="display:flex; justify-content:space-between; align-items:center; gap:1rem; flex-wrap:wrap;">
                <div style="flex:1; min-width:220px;">
                    <div style="color:#94a3b8; font-weight:600;">Counting up to 7:00:00</div>
                    <div id="countdown-clock" class="trainer-clock">{display_time}</div>
                    <div id="countdown-status" style="color:{'#34d399' if ready else '#cbd5e1'}; font-weight:700;">{"HIT REGISTER NOW" if ready else "Wait for 7:00:00"}</div>
                </div>
                <div style="flex:1; min-width:220px; text-align:right; color:#cbd5e1;">
                    <div style="font-size:2.5rem; font-weight:800;">7:00:00 AM</div>
                    <div style="opacity:0.7;">Simulated window</div>
                </div>
            </div>
        </div>
        <script>
        (function() {{
            const startTs = {st.session_state.round_started_at * 1000:.3f};
            const windowMs = {window_seconds * 1000:.3f};
            const clockEl = document.getElementById('countdown-clock');
            const statusEl = document.getElementById('countdown-status');
            const targetMs = Date.UTC(2000, 0, 1, 7, 0, 0, 0);
            const baseMs = targetMs - windowMs;
            const precisionDigits = {precision};
            const epochNow = () => performance.timeOrigin + performance.now();

            function format(elapsedMs) {{
                const clampedElapsed = Math.max(0, elapsedMs);
                const totalMs = baseMs + clampedElapsed;
                const dt = new Date(Math.floor(totalMs));
                const pad = (n) => n.toString().padStart(2, "0");
                const hours = pad(dt.getUTCHours());
                const minutes = pad(dt.getUTCMinutes());
                const secondsWhole = pad(dt.getUTCSeconds());
                if (precisionDigits > 0) {{
                    const fraction = ((totalMs % 1000) + 1000) % 1000;
                    const scaled = Math.floor((fraction / 1000) * (10 ** precisionDigits));
                    const padded = scaled.toString().padStart(precisionDigits, "0");
                    return `${{hours}}:${{minutes}}:${{secondsWhole}}.${{padded}}`;
                }}
                return `${{hours}}:${{minutes}}:${{secondsWhole}}`;
            }}

            function tick() {{
                const elapsedMs = epochNow() - startTs;
                const ready = elapsedMs >= windowMs;
                if (clockEl) {{
                    clockEl.textContent = format(elapsedMs);
                    clockEl.className = ready ? "trainer-clock trainer-ready" : "trainer-clock";
                }}
                if (statusEl) {{
                    statusEl.textContent = ready ? "HIT REGISTER NOW" : "Wait for 7:00:00";
                    statusEl.style.color = ready ? "#34d399" : "#cbd5e1";
                }}
                requestAnimationFrame(tick);
            }}

            tick();
        }})();
        </script>
        """,
        height=220,
    )

    st.button(
        "REGISTER",
        on_click=register_click,
        type="primary",
        use_container_width=True,
    )

    st.button(
        "🔄 Reset to next window",
        on_click=reset_attempt,
        help="Clear messages and jump to the next 7:00 AM slot.",
    )

    if st.session_state.last_result:
        if st.session_state.last_status == "warning":
            st.warning(st.session_state.last_result)
        else:
            st.success(st.session_state.last_result)
        st.caption("Resetting for the next attempt in about 3 seconds…")

    st.caption(
        f"Window: {base_time.strftime('%I:%M:%S').lstrip('0')} → 7:00:00 • "
        f"Precision: {precision_label(precision)}"
    )


def stats_tab() -> None:
    st.subheader("Performance pulse")
    if st.button("Reset statistics", type="secondary"):
        st.session_state.attempt_history = []
        st.experimental_rerun()

    attempts = st.session_state.get("attempt_history", [])
    if not attempts:
        st.info("No successful registrations yet.")
        return

    data = pd.DataFrame(attempts)
    max_time = float(data["reaction_s"].max()) if not data.empty else 0.0
    y_domain = [0, max_time * 1.05] if max_time > 0 else None

    metrics_col1, metrics_col2, metrics_col3, metrics_col4 = st.columns(4)
    metrics_col1.metric("Attempts", len(data))
    metrics_col2.metric("Mean (s)", f"{data['reaction_s'].mean():.3f}")
    metrics_col3.metric("Best (s)", f"{data['reaction_s'].min():.3f}")
    metrics_col4.metric("Settings used", str(data['setting'].nunique()))

    hist = (
        alt.Chart(data)
        .mark_bar(cornerRadiusTopLeft=6, cornerRadiusTopRight=6)
        .encode(
            alt.X("reaction_s:Q", bin=alt.Bin(maxbins=12), title="Reaction time (s)"),
            alt.Y("count()", title="Attempts"),
            alt.Color("precision_digits:N", title="Decimals"),
            tooltip=[alt.Tooltip("count()", title="Attempts"), "reaction_s:Q", "setting:N"],
        )
        .properties(height=220)
    )
    st.altair_chart(hist, use_container_width=True)

    line = (
        alt.Chart(data)
        .mark_line(point=True)
        .encode(
            x=alt.X("attempt_number:Q", title="Attempt #"),
            y=alt.Y(
                "reaction_s:Q",
                title="Reaction time (s)",
                scale=alt.Scale(domain=y_domain) if y_domain else alt.Undefined,
            ),
            color=alt.Color("setting:N", title="Setting"),
            tooltip=["attempt_number", "reaction_s:Q", "setting:N"],
        )
        .properties(height=220)
    )
    st.altair_chart(line, use_container_width=True)

    summary = (
        data.groupby(["setting", "precision_digits", "window_seconds"], as_index=False)
        .agg(
            attempts=("reaction_s", "count"),
            mean_s=("reaction_s", "mean"),
            best_s=("reaction_s", "min"),
        )
        .sort_values(["precision_digits", "window_seconds"])
    )
    summary["mean_s"] = summary["mean_s"].map(lambda value: round(float(value), 4))
    summary["best_s"] = summary["best_s"].map(lambda value: round(float(value), 4))
    st.dataframe(summary, use_container_width=True, hide_index=True)
    st.caption("Lower is better. Stats now track each exact timer setting instead of only two display buckets.")


def benchmark_tab() -> None:
    st.subheader("Benchmark comparison")
    st.write(
        f"Pick two timer settings, collect **{BENCHMARK_SAMPLES} successful samples each**, "
        "then compare their means with error bars."
    )

    if st.session_state.get("benchmark_notice"):
        if st.session_state.get("benchmark_notice_status") == "warning":
            st.warning(st.session_state.benchmark_notice)
        else:
            st.success(st.session_state.benchmark_notice)

    control_col1, control_col2 = st.columns(2)
    benchmark_active = bool(st.session_state.get("benchmark_active", False))

    with control_col1:
        st.markdown("#### Setting A")
        st.select_slider(
            "Decimals (A)",
            options=PRECISION_OPTIONS,
            key="benchmark_a_precision_digits",
            disabled=benchmark_active,
        )
        st.slider(
            "Lead time (A)",
            min_value=2.0,
            max_value=30.0,
            step=0.5,
            key="benchmark_a_window_seconds",
            disabled=benchmark_active,
        )

    with control_col2:
        st.markdown("#### Setting B")
        st.select_slider(
            "Decimals (B)",
            options=PRECISION_OPTIONS,
            key="benchmark_b_precision_digits",
            disabled=benchmark_active,
        )
        st.slider(
            "Lead time (B)",
            min_value=2.0,
            max_value=30.0,
            step=0.5,
            key="benchmark_b_window_seconds",
            disabled=benchmark_active,
        )

    action_col1, action_col2 = st.columns([1, 1])
    with action_col1:
        st.button(
            "Start benchmark",
            type="primary",
            use_container_width=True,
            disabled=benchmark_active,
            on_click=start_benchmark,
        )
    with action_col2:
        st.button(
            "Stop benchmark",
            use_container_width=True,
            disabled=not benchmark_active,
            on_click=stop_benchmark,
        )

    if benchmark_active:
        counts = benchmark_counts()
        progress_data = []
        for setting in st.session_state.get("benchmark_settings", []):
            setting_id = str(setting["id"])
            progress_data.append(
                {
                    "Setting": str(setting["name"]),
                    "Profile": setting_label(int(setting["precision_digits"]), float(setting["window_seconds"])),
                    "Completed": f"{counts.get(setting_id, 0)}/{BENCHMARK_SAMPLES}",
                }
            )
        st.dataframe(pd.DataFrame(progress_data), use_container_width=True, hide_index=True)
        st.caption("Successful clicks count as samples. Early clicks reset the round but do not count.")

    summary = benchmark_summary_frame()
    samples = st.session_state.get("benchmark_samples", [])
    if not samples:
        st.info("No benchmark samples yet. Start a run, then use the Countdown tab to take your 10 clicks.")
        return

    sample_data = pd.DataFrame(samples)
    current_run_id = int(st.session_state.get("benchmark_run_id", 0))
    sample_data = sample_data[sample_data["run_id"] == current_run_id].copy()
    if sample_data.empty or summary is None:
        st.info("No benchmark samples yet. Start a run, then use the Countdown tab to take your 10 clicks.")
        return

    metric_col1, metric_col2 = st.columns(2)
    for idx, row in summary.reset_index(drop=True).iterrows():
        delta = None
        if len(summary) == 2:
            other = summary.iloc[1 - idx]
            delta = row["mean_s"] - other["mean_s"]
        target_col = metric_col1 if idx == 0 else metric_col2
        target_col.metric(
            f"{row['setting_name']} mean",
            f"{row['mean_s']:.4f}s",
            f"{delta:+.4f}s vs other" if delta is not None else None,
        )
        target_col.caption(
            f"{row['setting_label']} • best {row['best_s']:.4f}s • SEM {row['sem_s']:.4f}s"
        )

    summary_chart = (
        alt.Chart(summary)
        .mark_bar(size=70, opacity=0.75)
        .encode(
            x=alt.X("setting_name:N", title="Benchmark setting"),
            y=alt.Y("mean_s:Q", title="Mean reaction time (s)"),
            color=alt.Color("setting_name:N", legend=None),
            tooltip=["setting_name", "setting_label", "samples", "mean_s", "sem_s", "best_s"],
        )
        .properties(height=280)
    )
    error_bars = (
        alt.Chart(summary)
        .mark_errorbar(ticks=True)
        .encode(
            x=alt.X("setting_name:N", title="Benchmark setting"),
            y="error_low:Q",
            y2="error_high:Q",
        )
    )
    st.altair_chart(summary_chart + error_bars, use_container_width=True)

    sample_points = (
        alt.Chart(sample_data)
        .mark_circle(size=90, opacity=0.8)
        .encode(
            x=alt.X("sample_number:Q", title="Sample #", scale=alt.Scale(domain=[1, BENCHMARK_SAMPLES])),
            y=alt.Y("reaction_s:Q", title="Reaction time (s)"),
            color=alt.Color("setting_name:N", title="Setting"),
            tooltip=["setting_name", "setting_label", "sample_number", "reaction_s"],
        )
        .properties(height=260)
    )
    sample_lines = (
        alt.Chart(sample_data)
        .mark_line(opacity=0.6)
        .encode(
            x="sample_number:Q",
            y="reaction_s:Q",
            color="setting_name:N",
        )
    )
    st.altair_chart(sample_lines + sample_points, use_container_width=True)
    st.caption("Error bars show ±1 standard error of the mean across the 5 successful samples.")


def main() -> None:
    st.set_page_config(page_title=APP_NAME, page_icon="⏱️")
    cool_styles()
    init_state()
    maybe_auto_reset()

    st.title(APP_NAME)
    st.write(
        "Practice the final stretch before **7:00:00 AM**. Adjust how early the clock starts "
        "so you can squeeze in more runs or take your time."
    )

    countdown_tab, stats_view, benchmark_view = st.tabs(["⏱️ Countdown", "📊 Stats", "🧪 Benchmark"])

    with countdown_tab:
        countdown_card()
    with stats_view:
        stats_tab()
    with benchmark_view:
        benchmark_tab()


if __name__ == "__main__":
    main()
