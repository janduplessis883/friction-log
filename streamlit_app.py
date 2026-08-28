from datetime import datetime

import pandas as pd
import streamlit as st
from streamlit_gsheets import GSheetsConnection


STAFF_MEMBERS = [
    "Jan",
    "Sally",
    "Tracy",
    "Siamma",
    "Selina",
    "Helen",
    "Zoe",

]

COLUMNS = [
    "recorded_at",
    "staff_member",
    "entry_type",
    "target_activity",
    "activity_count",
    "minutes_spent",
    "friction_point",
    "delay_minutes",
    "suggested_improvement",
]

ENTRY_TYPES = ["Work activity", "Friction point"]

BUTTON_ROW_PATTERN = [4, 3]

FIELD_HELP = {
    "recorded_at": (
        ""
    ),
    "target_activity": (
        "Describe the task completed or attempted. Keep it specific enough "
        "that someone else can understand the workflow, for example: scanning a "
        "referral, booking an appointment, or updating patient records."
    ),
    "activity_count": (
        "Use this when one entry represents a batch, such as processing 12 forms."
    ),
    "minutes_spent": (
        "Optional: record the approximate time spent on the activity."
    ),
    "friction_point": (
        "Explain what got in the way. Include the system, step, message, missing "
        "information, or handoff that made the task harder than expected."
    ),
    "delay_minutes": (
        "Estimate the extra time this caused. Use 0 minutes if it was annoying "
        "but did not noticeably delay the task."
    ),
    "suggested_improvement": (
        "Suggest what would make this easier next time. This can be a process "
        "change, template, training note, system setting, or anything else that "
        "would reduce the friction."
    ),
}


st.set_page_config(
    page_title="Activity / Friction Log",
    page_icon="",
    layout="centered",
)
st.logo("logo3.png", size="large")




def empty_log() -> pd.DataFrame:
    return pd.DataFrame(columns=COLUMNS)


@st.cache_data(ttl=30)
def read_log() -> pd.DataFrame:
    try:
        conn = st.connection("gsheets", type=GSheetsConnection)
        data = conn.read(ttl=0)
    except Exception:
        return empty_log()

    if data is None or data.empty:
        return empty_log()

    for column in COLUMNS:
        if column not in data.columns:
            data[column] = None

    # Keep existing friction rows meaningful after the sheet gains the new
    # activity fields.
    entry_type = data["entry_type"].fillna("").astype(str).str.strip()
    data["entry_type"] = entry_type.where(
        entry_type.isin(ENTRY_TYPES),
        data["friction_point"].fillna("").astype(str).str.strip().map(
            lambda value: "Friction point" if value else "Work activity"
        ),
    )

    return data[COLUMNS]


def append_log_entry(entry: dict) -> None:
    conn = st.connection("gsheets", type=GSheetsConnection)

    # The connection package's public update() method clears and rewrites the
    # worksheet. Use the configured gspread worksheet directly so each entry
    # is added as one new row instead.
    worksheet = conn.client._select_worksheet()
    worksheet.append_rows(
        [[entry[column] for column in COLUMNS]],
        value_input_option="USER_ENTERED",
        insert_data_option="INSERT_ROWS",
    )
    read_log.clear()


def reset_form() -> None:
    st.session_state.selected_staff = None
    st.session_state.form_version = st.session_state.get("form_version", 0) + 1


if "selected_staff" not in st.session_state:
    st.session_state.selected_staff = None
if "form_version" not in st.session_state:
    st.session_state.form_version = 0
if "show_entries" not in st.session_state:
    st.session_state.show_entries = False

log_df = read_log()
delay_minutes = pd.to_numeric(log_df["delay_minutes"], errors="coerce").fillna(0)

# st.sidebar.html(
#     """
#     <div style="
#         background: #101c28;
#         border: 2px solid #ec5d4b;
#         border-radius: 14px;
#         color: #ffffff;
#         font-size: 1.55rem;
#         font-weight: 900;
#         line-height: 1.1;
#         padding: 0.95rem 1rem;
#         margin-bottom: 1rem;
#     ">
#         Friction Log
#     </div>
#     """
# )

st.sidebar.metric(
    "Entries recorded",
    f"{len(log_df)}",
)
st.sidebar.metric(
    "Work activities",
    f"{(log_df['entry_type'] == 'Work activity').sum()}",
)
st.sidebar.metric(
    "Friction points",
    f"{(log_df['entry_type'] == 'Friction point').sum()}",
)
st.sidebar.metric(
    "Total delay time identified",
    f"{int(delay_minutes.sum())} mins",
)
st.sidebar.divider()
st.sidebar.markdown("**Google Sheet**")
st.sidebar.caption("Uses the private `gsheets` connection from `.streamlit/secrets.toml`.")
st.sidebar.markdown("**Staff**")
st.sidebar.caption(f"{len(STAFF_MEMBERS)} staff members configured.")

if st.session_state.show_entries:
    st.subheader(":shimmer[Recorded entries]")
    if log_df.empty:
        st.info("No entries recorded yet.")
    else:
        display_df = log_df.rename(
            columns={
                "recorded_at": "Recorded at",
                "staff_member": "Staff member",
                "entry_type": "Entry type",
                "target_activity": "Activity",
                "activity_count": "Count",
                "minutes_spent": "Minutes spent",
                "friction_point": "Friction point",
                "delay_minutes": "Delay minutes",
                "suggested_improvement": "Suggested improvement",
            }
        )
        st.dataframe(display_df, width="stretch", hide_index=True)
elif not st.session_state.selected_staff:
    st.html(
        """
        <style>
            [data-testid="stAppViewContainer"] {
                background: #ffffff;
            }

            [data-testid="stAppViewContainer"] > .main {
                background: transparent;
            }

            .block-container {
                position: relative;
                z-index: 1;
            }

            [data-testid="stButton"] {
                position: relative;
                z-index: 3;
            }

            .main-animated-bg {
                inset: 0;
                overflow: hidden;
                pointer-events: none;
                position: fixed;
                z-index: 2;
            }

            .moving-line {
                animation: line-drift 17s ease-in-out infinite;
                background: rgba(120, 128, 136, 0.28);
                height: 1px;
                left: 4%;
                position: absolute;
                top: 50%;
                transform: translateY(0);
                width: 92%;
            }

            .main-title-banner {
                animation: banner-rise 520ms ease-out both, banner-glow 7s ease-in-out infinite;
                background: linear-gradient(105deg, #101c28 0%, #101c28 48%, #344451 68%, #101c28 100%);
                background-size: 180% 180%;
                border: 1px solid transparent;
                border-radius: 25px;
                box-shadow: 0 26px 42px rgba(12, 23, 34, 0.14);
                color: #ffffff;
                margin-bottom: 1.6rem;
                padding: 2rem 2rem;
                position: relative;
                transition: border-color 140ms ease, box-shadow 140ms ease, transform 140ms ease;
                z-index: 3;
            }

            .main-title-banner:hover {
                border-color: #ec5d4b;
                box-shadow: 0 30px 48px rgba(12, 23, 34, 0.18);
                transform: translateY(-1px);
            }

            .main-title-kicker {
                color: rgba(255, 255, 255, 0.82);
                font-size: 0.95rem;
                font-weight: 400;
                letter-spacing: 0.12em;
                margin: 0 0 0.7rem;

            }

            .main-title-text {
                animation: title-focus 560ms ease-out 120ms both;
                color: #ffffff;
                font-size: 3.8rem;
                font-weight: 900;
                line-height: 0.95;
                margin: 0;
            }

            @keyframes banner-rise {
                from {
                    opacity: 0;
                    transform: translateY(10px);
                }
                to {
                    opacity: 1;
                    transform: translateY(0);
                }
            }

            @keyframes banner-glow {
                0%, 100% {
                    background-position: 0% 50%;
                }
                50% {
                    background-position: 100% 50%;
                }
            }

            @keyframes title-focus {
                from {
                    opacity: 0;
                    transform: translateX(-8px);
                }
                to {
                    opacity: 1;
                    transform: translateX(0);
                }
            }

            @keyframes line-drift {
                0% {
                    transform: translateY(-23vh);
                }
                19% {
                    transform: translateY(11vh);
                }
                43% {
                    transform: translateY(-7vh);
                }
                67% {
                    transform: translateY(25vh);
                }
                84% {
                    transform: translateY(-14vh);
                }
                100% {
                    transform: translateY(-23vh);
                }
            }
        </style>
        <div class="main-animated-bg" aria-hidden="true">
            <span class="moving-line"></span>
        </div>
        <div class="main-title-banner">
            <p class="main-title-kicker">Workflow Intelligence</p>
            <h1 class="main-title-text">Activity / Friction Log</h1>
        </div>
        """
    )



if not st.session_state.selected_staff and not st.session_state.show_entries:
    st.space(30)
    row_start = 0
    row_index = 0
    while row_start < len(STAFF_MEMBERS):
        buttons_in_row = BUTTON_ROW_PATTERN[row_index % len(BUTTON_ROW_PATTERN)]
        row_members = STAFF_MEMBERS[row_start : row_start + buttons_in_row]
        row = st.columns(buttons_in_row)
        for column, member in zip(row, row_members):
            with column:
                if st.button(f"**{member}**", type="primary", width="stretch", icon=":material/person:"):
                    st.session_state.selected_staff = member
                    st.rerun()
        row_start += buttons_in_row
        row_index += 1
        if row_start < len(STAFF_MEMBERS):
            st.space(1)

if st.session_state.selected_staff and not st.session_state.show_entries:
    staff_member = st.session_state.selected_staff
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    version = st.session_state.form_version

    st.subheader(f":shimmer[Entry for {staff_member}]")
    entry_type = st.segmented_control(
        "What are you recording?",
        options=ENTRY_TYPES,
        default=ENTRY_TYPES[0],
        key=f"entry_type_{version}",
    )
    with st.form(f"friction_form_{version}", clear_on_submit=True):
        # st.text_input("Date & Time", value=now, disabled=True)
        st.markdown(f":material/date_range:`{now}`")
        st.caption(FIELD_HELP["recorded_at"])
        target_activity = st.text_input(
            "**Activity**",
            placeholder="Process referral forms",
            help=FIELD_HELP["target_activity"],
            key=f"target_activity_{version}",
        )
        if entry_type == "Work activity":
            activity_count = st.number_input(
                "**Number completed**",
                min_value=1,
                value=1,
                step=1,
                help=FIELD_HELP["activity_count"],
                key=f"activity_count_{version}",
            )
            minutes_spent = st.number_input(
                "**Minutes spent (optional)**",
                min_value=0,
                value=0,
                step=5,
                help=FIELD_HELP["minutes_spent"],
                key=f"minutes_spent_{version}",
            )
            friction_point = ""
            delay = 0
            suggested_improvement = ""
        else:
            activity_count = 1
            minutes_spent = 0
            friction_point = st.text_area(
                "**Obstacle / friction point**",
                placeholder="System auto-attached 3 patient files together",
                help=FIELD_HELP["friction_point"],
                key=f"friction_point_{version}",
            )
            delay = st.selectbox(
                "**Delay time**",
                options=list(range(0, 125, 5)),
                format_func=lambda minutes: f"{minutes} mins",
                index=3,
                help=FIELD_HELP["delay_minutes"],
                key=f"delay_{version}",
            )
            suggested_improvement = st.text_area(
                "**Suggested improvement**",
                placeholder="Separate pages in document management before filling.",
                help=FIELD_HELP["suggested_improvement"],
                key=f"suggested_improvement_{version}",
            )

        submitted = st.form_submit_button(
            f"**Record {entry_type.lower() if entry_type else 'entry'}**",
            type="primary",
            width="stretch",
            icon=":material/upload:",
        )

    cancel = st.button("Cancel entry", width="stretch", icon=":material/cancel:")

    if cancel:
        reset_form()
        st.rerun()

    if submitted:
        missing_fields = [
            label
            for label, value in {
                "Activity": target_activity,
                **(
                    {
                        "Obstacle / Friction Point": friction_point,
                        "Suggested Improvement": suggested_improvement,
                    }
                    if entry_type == "Friction point"
                    else {}
                ),
            }.items()
            if not value.strip()
        ]

        if missing_fields:
            st.error(f"Please complete: {', '.join(missing_fields)}.")
        else:
            try:
                append_log_entry(
                    {
                        "recorded_at": now,
                        "staff_member": staff_member,
                        "entry_type": entry_type,
                        "target_activity": target_activity.strip(),
                        "activity_count": int(activity_count),
                        "minutes_spent": int(minutes_spent),
                        "friction_point": friction_point.strip(),
                        "delay_minutes": int(delay),
                        "suggested_improvement": suggested_improvement.strip(),
                    }
                )
            except Exception as exc:
                st.error(
                    "Could not save to Google Sheets. Check `.streamlit/secrets.toml`, "
                    "the spreadsheet URL, service account access, and edit permissions."
                )
                st.caption(str(exc))
            else:
                st.success(f"{entry_type} recorded.")
                reset_form()
                st.rerun()
