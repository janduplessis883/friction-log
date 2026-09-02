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
    jobs["job_label"] = jobs["job"]
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

gantt_expander = st.expander(":material/timeline: Time spent per activity", expanded=True)
gantt_expander.caption(
    "Estimated from each work or break entry until the next event logged by the same staff member. "
    "Gaps longer than 8 hours and entries without a following timestamp are omitted."
)
all_job_gantt = build_job_gantt(filtered)

analysis_expander = st.expander(":material/analytics: User analysis", expanded=False)
daily_expander = st.expander(":material/trending_up: Daily trends and activity", expanded=False)
if all_job_gantt.empty:
    gantt_expander.info("Not enough work or break entries with consecutive timestamps to estimate activity time.")
else:
    all_job_gantt["_time_per_unit"] = all_job_gantt["duration_minutes"].div(
        all_job_gantt["activity_count"].where(all_job_gantt["activity_count"].gt(0))
    )
    gantt_staff_options = sorted(all_job_gantt["staff_member"].unique())
    selected_gantt_staff = gantt_expander.selectbox(
        "Staff member",
        options=gantt_staff_options,
        help="Choose which staff member's job timeline to display.",
        key="gantt_staff_member",
    )
    job_gantt = all_job_gantt[
        all_job_gantt["staff_member"] == selected_gantt_staff
    ].copy()

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
                title=None,
                sort="-x",
                axis=alt.Axis(
                    labelLimit=280,
                    grid=True,
                    gridColor="#ECEFF1",
                    gridOpacity=0.85,
                    gridWidth=1,
                ),
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
    gantt_expander.altair_chart(gantt)

    category_summary = (
        job_gantt.groupby("job", as_index=False)
        .agg(
            total_time_minutes=("duration_minutes", "sum"),
            total_units=("activity_count", "sum"),
        )
        .rename(
            columns={
                "job": "Activity",
                "total_time_minutes": "Total Time (min)",
                "total_units": "Total units",
            }
        )
    )
    category_summary["Total Time (min)"] = category_summary[
        "Total Time (min)"
    ].round(1)
    category_summary["Total Time (hrs)"] = (
        category_summary["Total Time (min)"].div(60).round(2)
    )
    units = category_summary["Total units"].where(
        category_summary["Total units"].gt(0)
    )
    category_summary["Time per unit (min)"] = (
        category_summary["Total Time (min)"].div(units).round(1)
    )
    time_per_unit_trends = job_gantt.groupby("job")["_time_per_unit"].apply(
        lambda values: values.dropna().round(1).tolist()
    )
    category_summary["Time per unit trend"] = category_summary["Activity"].map(
        time_per_unit_trends
    ).apply(lambda values: values if isinstance(values, list) else [])
    category_summary = category_summary[
        [
            "Activity",
            "Total Time (min)",
            "Total Time (hrs)",
            "Total units",
            "Time per unit (min)",
            "Time per unit trend",
        ]
    ].sort_values("Activity", ascending=True)
    gantt_expander.dataframe(
        category_summary,
        width="stretch",
        hide_index=True,
        column_config={
            "Time per unit trend": st.column_config.LineChartColumn(
                "Time per unit trend (min)",
                width="medium",
                help="Per-entry time per unit for this activity, in minutes.",
                y_min=0,
            )
        },
    )

    work_jobs = all_job_gantt[all_job_gantt["entry_type"].eq("Work activity")].copy()
    user_metric_rows = []
    for staff_member, user_jobs in work_jobs.groupby("staff_member"):
        per_unit = user_jobs["_time_per_unit"].dropna()
        mean_per_unit = per_unit.mean()
        consistency = (
            round(per_unit.std(ddof=0) / mean_per_unit * 100, 1)
            if len(per_unit) > 1 and mean_per_unit > 0
            else None
        )
        ordered_jobs = user_jobs.sort_values("recorded_at")
        context_switches = max(
            0,
            int(ordered_jobs["job"].ne(ordered_jobs["job"].shift()).sum() - 1),
        )
        user_metric_rows.append(
            {
                "User": staff_member,
                "Median time per unit (min)": round(per_unit.median(), 1)
                if not per_unit.empty
                else None,
                "Estimated work time (hrs)": round(
                    user_jobs["duration_minutes"].sum() / 60, 2
                ),
                "Total units": int(user_jobs["activity_count"].sum()),
                "Context switches": context_switches,
                "Consistency (CV %)": consistency,
            }
        )

    if user_metric_rows:
        analysis_expander.caption(
            "Median time per unit is the middle per-unit time, so lower values generally indicate faster throughput. "
            "Estimated work time is the total inferred time spent working, while Total units is completed volume. "
            "Context switches count changes between consecutive work categories; lower values may indicate fewer interruptions. "
            "Consistency (CV %) measures variation relative to average time per unit; lower percentages indicate more consistent timings."
        )
        analysis_expander.dataframe(
            pd.DataFrame(user_metric_rows).sort_values("User"),
            width="stretch",
            hide_index=True,
        )
    else:
        analysis_expander.info("No qualifying work activities are available for user analysis.")

    time_distribution = (
        work_jobs.groupby(["staff_member", "job"], as_index=False)["duration_minutes"]
        .sum()
        .rename(
            columns={
                "staff_member": "User",
                "job": "Activity",
                "duration_minutes": "Time (min)",
            }
        )
    )
    time_distribution["Time distribution (%)"] = (
        time_distribution["Time (min)"]
        / time_distribution.groupby("User")["Time (min)"].transform("sum")
        * 100
    ).round(1)
    if time_distribution.empty:
        analysis_expander.info("No time distribution is available for the selected range.")
    else:
        analysis_expander.caption(
            "Time (min) is the estimated time spent on each activity. Time distribution (%) is that activity's share of the user's estimated work time; higher percentages show where most time is being spent."
        )
        analysis_expander.dataframe(
            time_distribution.sort_values(
                ["User", "Time (min)"], ascending=[True, False]
            ),
            width="stretch",
            hide_index=True,
        )

        daily_user_time = (
            work_jobs.assign(Date=work_jobs["recorded_at"].dt.date)
            .groupby(["Date", "staff_member"])["duration_minutes"]
            .sum()
            .unstack(fill_value=0)
            .sort_index()
        )
        daily_expander.caption(
            "Daily trend shows each user's estimated work time by day. Look for sustained changes or unusual spikes rather than judging a single day."
        )
        daily_expander.line_chart(daily_user_time, y_label="Estimated work time (minutes)")

daily_activity = (
    work.assign(day=work["recorded_at"].dt.date)
    .groupby(["day", "staff_member"], as_index=False)["activity_count"]
    .sum()
    .pivot(index="day", columns="staff_member", values="activity_count")
    .fillna(0)
    .sort_index()
)
if daily_activity.empty:
    daily_expander.info("No daily work activity matches the selected filters.")
else:
    daily_expander.caption(
        "Daily activity shows completed units by day and user. Compare this with the time trend to distinguish higher workload from slower throughput."
    )
    daily_expander.line_chart(daily_activity, y_label="Completed units")

st.subheader("Entries by staff member")
entry_summary = (
    filtered.groupby(["staff_member", "entry_type"])
    .size()
    .unstack(fill_value=0)
    .reindex(columns=ENTRY_TYPES, fill_value=0)
)
st.bar_chart(entry_summary)
