import time
from datetime import datetime, timedelta
from typing import List, Optional

import altair as alt
import numpy as np
import pandas as pd
import streamlit as st
import streamlit.components.v1 as components


WINDOW_SECONDS = 10.0  # from 6:59:50 to 7:00:00
RESET_DELAY = 2.0
BASE_TIME = datetime(2000, 1, 1, 6, 59, 50)  # purely display, not real clock


def format_clock(elapsed: float, show_millis: bool) -> str:
    base = BASE_TIME + timedelta(seconds=max(0.0, elapsed))
    if show_millis:
        return base.strftime("%I:%M:%S.%f %p").lstrip("0")[:-3]
    return base.strftime("%I:%M:%S %p").lstrip("0")


def format_remaining(seconds: float, show_millis: bool) -> str:
    total = max(0.0, seconds)
    h = int(total // 3600)
    m = int((total % 3600) // 60)
    s = total % 60
    if show_millis:
        return f"{h:02d}:{m:02d}:{s:06.3f}"
    return f"{h:02d}:{m:02d}:{s:05.2f}"


def init_state() -> None:
    if "round_started_at" not in st.session_state:
        st.session_state.round_started_at = time.time()
        st.session_state.last_result: Optional[str] = None
        st.session_state.last_status: Optional[str] = None
        st.session_state.reaction_times: List[float] = []
        st.session_state.next_reset_at: Optional[float] = None


def reset_attempt() -> None:
    st.session_state.round_started_at = time.time()
    st.session_state.last_result = None
    st.session_state.last_status = None
    st.session_state.next_reset_at = None


def elapsed_seconds() -> float:
    return max(0.0, time.time() - st.session_state.round_started_at)


def register_click() -> None:
    elapsed = elapsed_seconds()
    if elapsed < WINDOW_SECONDS:
        remaining = WINDOW_SECONDS - elapsed
        st.session_state.last_status = "warning"
        st.session_state.last_result = (
            f"Too early! {format_remaining(remaining, st.session_state.get('show_ms', False))} "
            "remain before 7:00:00."
        )
    else:
        reaction = elapsed - WINDOW_SECONDS
        st.session_state.reaction_times.append(reaction)
        st.session_state.last_status = "success"
        st.session_state.last_result = (
            f"Registered {reaction:.3f}s after 7:00:00. Nice reflexes!"
        )
    st.session_state.next_reset_at = time.time() + RESET_DELAY


def maybe_auto_reset() -> None:
    if st.session_state.next_reset_at and time.time() >= st.session_state.next_reset_at:
        reset_attempt()


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
    show_ms = st.toggle("Show milliseconds", value=False, key="show_ms")
    elapsed = elapsed_seconds()
    remaining = WINDOW_SECONDS - elapsed
    ready = remaining <= 0.0
    display_time = format_clock(elapsed, show_ms)

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
            const startTs = {int(st.session_state.round_started_at * 1000)};
            const windowMs = {int(WINDOW_SECONDS * 1000)};
            const clockEl = document.getElementById('countdown-clock');
            const statusEl = document.getElementById('countdown-status');
            const baseMs = Date.UTC(2000, 0, 1, 6, 59, 50, 0);
            const showMs = {"true" if show_ms else "false"};

            function format(remainingMs) {{
                const dt = new Date(baseMs + Math.max(0, remainingMs));
                const pad = (n) => n.toString().padStart(2, "0");
                const hours = pad(dt.getUTCHours());
                const minutes = pad(dt.getUTCMinutes());
                const seconds = pad(dt.getUTCSeconds());
                if (showMs) {{
                    const millis = dt.getUTCMilliseconds().toString().padStart(3, "0");
                    return `${{hours}}:${{minutes}}:${{seconds}}.${{millis}}`;
                }}
                return `${{hours}}:${{minutes}}:${{seconds}}`;
            }}

            function tick() {{
                const now = Date.now();
                const elapsedMs = now - startTs;
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
        st.caption("Resetting for the next attempt…")

    st.caption(
        f"Window: 6:59:50 → 7:00:00 • "
        f"Mode: {'milliseconds' if show_ms else 'hundredths'}"
    )


def stats_tab() -> None:
    st.subheader("Performance pulse")
    times = st.session_state.reaction_times
    if not times:
        st.info("No reaction times yet. Nail a registration to start building your chart.")
        return

    data = pd.DataFrame({"reaction_s": times})
    metrics_col1, metrics_col2, metrics_col3, metrics_col4 = st.columns(4)
    metrics_col1.metric("Attempts", len(times))
    metrics_col2.metric("Mean (s)", f"{np.mean(times):.3f}")
    metrics_col3.metric("Best (s)", f"{np.min(times):.3f}")
    metrics_col4.metric("90th %ile (s)", f"{np.percentile(times, 90):.3f}")

    st.markdown("#### Distribution")
    hist = (
        alt.Chart(data)
        .mark_bar(cornerRadiusTopLeft=6, cornerRadiusTopRight=6)
        .encode(
            alt.X("reaction_s:Q", bin=alt.Bin(maxbins=12), title="Reaction time (s)"),
            alt.Y("count()", title="Attempts"),
            tooltip=[alt.Tooltip("count()", title="Attempts"), "reaction_s:Q"],
        )
        .properties(height=240)
    )
    mean_line = (
        alt.Chart(pd.DataFrame({"mean": [np.mean(times)]}))
        .mark_rule(color="#38bdf8", strokeDash=[6, 4])
        .encode(x="mean:Q")
    )
    st.altair_chart(hist + mean_line, use_container_width=True)

    st.markdown("#### Recent streak")
    streak = data.reset_index().rename(columns={"index": "attempt"})
    line = (
        alt.Chart(streak)
        .mark_line(point=True)
        .encode(
            x=alt.X("attempt:Q", title="Attempt #"),
            y=alt.Y("reaction_s:Q", title="Reaction time (s)"),
            tooltip=["attempt", "reaction_s:Q"],
        )
        .properties(height=240)
    )
    st.altair_chart(line, use_container_width=True)

    st.caption(
        "Lower is better. Aim to click just after the clock hits 7:00:00 to shave down your average."
    )


def main() -> None:
    st.set_page_config(page_title="Class Registration Reflex Trainer", page_icon="⏱️")
    cool_styles()
    init_state()
    maybe_auto_reset()

    st.title("Class Registration Reflex Trainer")
    st.write(
        "Practice the last 10 seconds before **7:00:00 AM**. The timer loops from "
        "6:59:50 to 7:00:00 so you can drill your reaction."
    )

    countdown_tab, stats_view = st.tabs(["⏱️ Countdown", "📊 Stats"])

    with countdown_tab:
        countdown_card()
    with stats_view:
        stats_tab()


if __name__ == "__main__":
    main()
