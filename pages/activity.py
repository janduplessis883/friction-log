from datetime import timedelta

import pandas as pd
import streamlit as st
import altair as alt
from streamlit_gsheets import GSheetsConnection
from zoneinfo import ZoneInfo


PIN = "5234"
COLUMNS = [
    "recorded_at",
    "staff_member",
    "entry_type",
    "target_activity",
    "activity_count",
    "friction_point",
    "delay_minutes",
    "suggested_improvement",
    "break_type",
    "break_note",
]
ENTRY_TYPES = ["Work activity", "Friction point", "Break"]
LONDON_TZ = ZoneInfo("Europe/London")


def parse_london_timestamp(value):
    """Parse both legacy naive values and new timezone-aware log values."""
    if pd.isna(value) or str(value).strip() == "":
        return pd.NaT
    try:
        timestamp = pd.Timestamp(value)
    except (TypeError, ValueError):
        return pd.NaT
    if timestamp.tzinfo is None:
        return timestamp.tz_localize(LONDON_TZ)
    return timestamp.tz_convert(LONDON_TZ)


st.set_page_config(page_title="Activity dashboard", page_icon=":material/insights:", layout="wide")
st.logo("logo3.png", size="large")

with st.container(horizontal=True, vertical_alignment="center"):
    st.page_link(
        "streamlit_app.py",
        label="Log an entry",
        icon=":material/edit_note:",
    )
    st.page_link(
        "pages/activity.py",
        label="Activity dashboard",
        icon=":material/insights:",
    )


@st.cache_data(ttl=30)
def read_log() -> pd.DataFrame:
    try:
        conn = st.connection("gsheets", type=GSheetsConnection)
        data = conn.read(ttl=0)
    except Exception:
        return pd.DataFrame(columns=COLUMNS)

    if data is None or data.empty:
        return pd.DataFrame(columns=COLUMNS)

    for column in COLUMNS:
        if column not in data.columns:
            data[column] = None
    return data[COLUMNS]


def unlock() -> None:
    entered_pin = st.session_state.get("activity_pin", "")
    if entered_pin == PIN:
        st.session_state.activity_unlocked = True
        st.session_state.activity_pin_error = False
    else:
        st.session_state.activity_pin_error = True


if "activity_unlocked" not in st.session_state:
    st.session_state.activity_unlocked = False
if "activity_pin_error" not in st.session_state:
    st.session_state.activity_pin_error = False


if not st.session_state.activity_unlocked:
    st.title(":material/lock: Activity dashboard")
    st.write("Enter the PIN to view activity patterns across the team.")
    with st.form("activity_pin_form", border=False):
        st.text_input(
            "Dashboard PIN",
            type="password",
            max_chars=4,
            key="activity_pin",
            autocomplete="off",
        )
        st.form_submit_button(
            "Unlock dashboard",
            type="primary",
            width="content",
            icon=":material/lock_open:",
            on_click=unlock,
        )
    if st.session_state.activity_pin_error:
        st.error("That PIN is not correct.")
    st.stop()


st.title(":material/insights: Activity dashboard")
st.caption("A view of recorded work, friction, and breaks by staff member.")

log_df = read_log().copy()
if log_df.empty:
    st.info("No activity has been recorded yet.")
    st.stop()

log_df["activity_count"] = pd.to_numeric(log_df["activity_count"], errors="coerce").fillna(0)
parsed_recorded_at = log_df["recorded_at"].map(parse_london_timestamp)
# Keep London wall-clock values for Altair so the chart does not reinterpret them
# using the browser's timezone.
log_df["recorded_at"] = pd.to_datetime(parsed_recorded_at).dt.tz_localize(None)
log_df["staff_member"] = log_df["staff_member"].fillna("Unknown").astype(str).str.strip()
log_df["entry_type"] = log_df["entry_type"].fillna("Unknown").astype(str).str.strip()
log_df = log_df.dropna(subset=["recorded_at"])

if log_df.empty:
    st.info("The log does not contain any entries with valid dates yet.")
    st.stop()

with st.sidebar:
    st.subheader("Dashboard filters")
    staff_options = sorted(log_df["staff_member"].unique())
    selected_staff = st.multiselect("Staff", staff_options, default=staff_options)
    min_date = log_df["recorded_at"].dt.date.min()
    max_date = log_df["recorded_at"].dt.date.max()
    selected_dates = st.slider(
        "Date range",
        min_value=min_date,
        max_value=max_date,
        value=(min_date, max_date),
        format="DD/MM/YYYY",
        step=timedelta(days=1),
    )
    if st.button("Lock dashboard", icon=":material/lock:"):
        st.session_state.activity_unlocked = False
        st.rerun()

if not selected_staff:
    st.warning("Select at least one staff member to view the charts.")
    st.stop()

start_date, end_date = selected_dates

filtered = log_df[
    log_df["staff_member"].isin(selected_staff)
    & log_df["recorded_at"].dt.date.between(start_date, end_date)
].copy()

work = filtered[filtered["entry_type"] == "Work activity"]
friction = filtered[filtered["entry_type"] == "Friction point"]
breaks = filtered[filtered["entry_type"] == "Break"]


def build_job_gantt(log_entries: pd.DataFrame) -> pd.DataFrame:
    """Estimate work and break spans until the next event for the same staff member."""
    events = log_entries.sort_values(["staff_member", "recorded_at"]).copy()
    events["end"] = events.groupby("staff_member")["recorded_at"].shift(-1)
    work_mask = (
        events["entry_type"].eq("Work activity")
        & events["target_activity"].fillna("").astype(str).str.strip().ne("")
    )
    jobs = events[work_mask | events["entry_type"].eq("Break")].copy()
    if jobs.empty:
        return pd.DataFrame()

    jobs["duration_minutes"] = (
        jobs["end"].sub(jobs["recorded_at"]).dt.total_seconds().div(60)
    )
    # An overnight or unusually long gap is not a reliable estimate of time
    # spent on the preceding job, so keep only same-day workday-sized spans.
    jobs = jobs[
        jobs["end"].notna()
        & jobs["end"].dt.date.eq(jobs["recorded_at"].dt.date)
        & jobs["duration_minutes"].between(1, 8 * 60)
    ].copy()
    jobs["job"] = jobs["target_activity"].fillna("").astype(str).str.strip()
    break_name = jobs["break_type"].fillna("").astype(str).str.strip()
    jobs.loc[jobs["entry_type"].eq("Break"), "job"] = (
        "Break" + break_name.where(break_name.eq(""), " · " + break_name)
    )
    jobs["job_label"] = jobs["job"] + " · " + jobs["staff_member"]
    return jobs

with st.container(horizontal=True):
    st.metric("Work units completed", f"{int(work['activity_count'].sum()):,}", border=True)
    st.metric("Work entries", f"{len(work):,}", border=True)
    st.metric("Friction points", f"{len(friction):,}", border=True)
    st.metric("Breaks recorded", f"{len(breaks):,}", border=True)

st.subheader("Activity by staff member")
activity_by_user = (
    work.groupby("staff_member", as_index=False)["activity_count"]
    .sum()
    .rename(columns={"activity_count": "Work units"})
    .sort_values("Work units", ascending=False)
)
if activity_by_user.empty:
    st.info("No work activity matches the selected filters.")
else:
    st.bar_chart(
        activity_by_user,
        x="staff_member",
        y="Work units",
        horizontal=True,
        height=max(280, 56 * len(activity_by_user)),
    )

st.subheader("Time spent per activity")
st.caption(
    "Estimated from each work or break entry until the next event logged by the same staff member. "
    "Gaps longer than 8 hours and entries without a following timestamp are omitted."
)
job_gantt = build_job_gantt(filtered)
if job_gantt.empty:
    st.info("Not enough work or break entries with consecutive timestamps to estimate activity time.")
else:
    gantt_staff_options = sorted(job_gantt["staff_member"].unique())
    selected_gantt_staff = st.selectbox(
        "Staff member",
        options=gantt_staff_options,
        help="Choose which staff member's job timeline to display.",
        key="gantt_staff_member",
    )
    job_gantt = job_gantt[job_gantt["staff_member"] == selected_gantt_staff].copy()

    gantt = (
        alt.Chart(job_gantt)
        .mark_bar(cornerRadius=3, height=18)
        .encode(
            x=alt.X(
                "recorded_at:T",
                title="Recorded time",
                axis=alt.Axis(format="%H:%M"),
            ),
            x2="end:T",
            y=alt.Y(
                "job_label:N",
                title="Job · staff member",
                sort="-x",
                axis=alt.Axis(labelLimit=280),
            ),
            color=alt.Color(
                "entry_type:N",
                title="Activity type",
                scale=alt.Scale(
                    domain=["Work activity", "Break"],
                    range=["#243447", "#F59E0B"],
                ),
            ),
            tooltip=[
                alt.Tooltip("entry_type:N", title="Activity type"),
                alt.Tooltip("job:N", title="Job"),
                alt.Tooltip("staff_member:N", title="Staff member"),
                alt.Tooltip("recorded_at:T", title="Started", format="%d %b %Y, %H:%M"),
                alt.Tooltip("end:T", title="Next event", format="%d %b %Y, %H:%M"),
                alt.Tooltip("duration_minutes:Q", title="Estimated minutes", format=".1f"),
            ],
        )
        # Give every activity row enough vertical space for its y-axis label.
        .properties(height=max(240, 42 * job_gantt["job_label"].nunique()))
    )
    st.altair_chart(gantt)

st.subheader("Daily work activity")
daily_activity = (
    work.assign(day=work["recorded_at"].dt.date)
    .groupby(["day", "staff_member"], as_index=False)["activity_count"]
    .sum()
    .pivot(index="day", columns="staff_member", values="activity_count")
    .fillna(0)
    .sort_index()
)
if daily_activity.empty:
    st.info("No daily work activity matches the selected filters.")
else:
    st.line_chart(daily_activity)

st.subheader("Entries by staff member")
entry_summary = (
    filtered.groupby(["staff_member", "entry_type"])
    .size()
    .unstack(fill_value=0)
    .reindex(columns=ENTRY_TYPES, fill_value=0)
)
st.bar_chart(entry_summary)
