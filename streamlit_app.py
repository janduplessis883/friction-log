from datetime import datetime
from zoneinfo import ZoneInfo

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
    "Hunter",
]

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
GOOGLE_SHEET_URL = "https://docs.google.com/spreadsheets/d/1SJsxuSaTb0kM5iIpCm82Jyy09Vpu19UX_Rkbe1uNWIs/edit?usp=sharing"
ACTIVITY_OPTIONS = [
    "2WW Referrals",
    "2WW Tracking",
    "Accounts Admin",
    "Administration",
    "Annual Leave request",
    "Answering Telephone Calls",
    "Automation Python",
    "Booking Appointments",
    "Cancelling Clinics",
    "Cancelling Individual Patients",
    "Clinical Correspondence",
    "Complaints Administration",
    "CQRS",
    "Dealing with Letters",
    "Dictation",
    "District Nurse Coordination",
    "ECS Training",
    "Email Administration",
    "eRS Worklists",
    "Excel Sheets",
    "Facilities, Supplies and Premises Management",
    "Flu - Housebound",
    "Flu planning",
    "FP34 - ECS",
    "FP34 - SMW",
    "Friends & Family Test",
    "Handling Reception Queries",
    "ImmForm - Ordering Imms",
    "Immunisation Recalls",
    "Insurance and Medical Report Requests",
    "IT Problems and Issues",
    "Leaving for the Day Routine",
    "Loading New Appointments",
    "Managing SystmOne Tasks",
    "Managing Test Results",
    "Mandatory Training - e-Learning",
    "Medication Change Letters to Pts",
    "Meeting Preparation",
    "Meetings and Team Coordination",
    "Moving Patient Appointments",
    "Opening Letters",
    "Paying Bills",
    "PPG Meeting Planning",
    "Prescription Administration",
    "Prescription Requests",
    "Processing Forms",
    "Processing Personal NHS Mail",
    "Processing Referrals",
    "Processing Subject Access Requests (SAR)",
    "Processing Surgery NHS Mail",
    "Processing Telephone Data for PCN",
    "Recall and Screening Administration",
    "Registration and Deductions",
    "Review Targets Dashboards",
    "Reviewing SystmOne Appointments",
    "Scanning and Filing Letters",
    "Sick Leave - Cancelling Clinics",
    "Sick Leave - Receiving Call / WhatsApp",
    "Sorting Through Papers and Computer Files",
    "Staff Relationship Discussion",
    "Staff Rotas",
    "Staff Training and Onboarding",
    "Stamping Envelopes",
    "SystmOne Searches",
    "SystmOne Tasks",
    "Sympathy Letter",
    "Targets Admin",
    "Updating or Cancelling Appointments",
    "Updating Patient Records",
]
ACTIVITY_OPTIONS.append("Other")
BREAK_TYPES = [
    "Lunch",
    "Scheduled break",

    "Comfort break",

    "End of working day",
]

BUTTON_ROW_PATTERN = [4, 3]

FIELD_HELP = {
    "recorded_at": (
        ""
    ),
    "target_activity": (
        "Choose a standard activity or type a custom activity. Keep it specific "
        "enough that someone else can understand the workflow."
    ),
    "activity_count": (
        "Use this when one entry represents a batch, such as processing 12 forms."
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
    "break_note": "Optional: add context about the break or what prompted it.",
}


st.set_page_config(
    page_title="Activity / Friction Log",
    page_icon="",
    layout="centered",
)
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




def empty_log() -> pd.DataFrame:
    return pd.DataFrame(columns=COLUMNS)


@st.cache_data(ttl=30)
def read_log() -> pd.DataFrame:
    try:
        conn = st.connection("gsheets", type=GSheetsConnection)
        migrate_sheet_layout(conn.client._select_worksheet())
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


def render_staff_statuses(log_df: pd.DataFrame) -> None:
    """Show each staff member's status from their most recent log entry."""
    latest_by_staff = {}
    if not log_df.empty:
        dated_log = log_df.copy()
        dated_log["_recorded_at"] = pd.to_datetime(
            dated_log["recorded_at"], errors="coerce", utc=True
        )
        dated_log = dated_log.sort_values("_recorded_at", na_position="first")
        latest_by_staff = dated_log.drop_duplicates(
            subset="staff_member", keep="last"
        ).set_index("staff_member").to_dict("index")

    _, status_column, _ = st.columns([0.7, 5, 0.7])
    with status_column:
        with st.container(
            horizontal=True,
            horizontal_alignment="center",
            gap="small",
        ):
            for staff_member in STAFF_MEMBERS:
                latest_entry = latest_by_staff.get(staff_member)
                if latest_entry is None:
                    st.badge(
                        staff_member,
                        color="gray",
                        help="No entry recorded yet.",
                    )
                    continue

                entry_type = str(latest_entry.get("entry_type", "")).strip()
                break_type = str(latest_entry.get("break_type", "")).strip()
                break_note = str(latest_entry.get("break_note", "")).strip()
                end_of_day = "end of working day" in f"{break_type} {break_note}".casefold()

                if entry_type == "Break" and end_of_day:
                    color = "gray"
                    status = "End of working day"
                elif entry_type == "Break":
                    color = "yellow"
                    status = "On a break"
                else:
                    color = "green"
                    status = "Working"

                st.badge(staff_member, color=color, help=status)


def append_log_entry(entry: dict) -> None:
    conn = st.connection("gsheets", type=GSheetsConnection)

    worksheet = conn.client._select_worksheet()

    # The sheet previously used a 9-column layout without target_activity.
    # Migrate that layout before appending so old rows remain meaningful and
    # new rows cannot be written under stale or duplicate headers.
    migrate_sheet_layout(worksheet)

    # Use the configured gspread worksheet directly so each entry is added as
    # one new row instead of clearing and rewriting the worksheet on every save.
    worksheet.append_rows(
        [[entry[column] for column in COLUMNS]],
        value_input_option="USER_ENTERED",
        insert_data_option="INSERT_ROWS",
    )
    read_log.clear()


def migrate_sheet_layout(worksheet) -> None:
    expected_headers = COLUMNS
    rows = worksheet.get_all_values()
    if not rows or not any(str(value).strip() for value in rows[0]):
        worksheet.update(
            range_name="A1:J1",
            values=[expected_headers],
            value_input_option="USER_ENTERED",
        )
        return

    headers = [str(value).strip() for value in rows[0]]
    if headers == expected_headers:
        return

    normalized_rows = [expected_headers]
    for raw_row in rows[1:]:
        values = list(raw_row) + [""] * (10 - len(raw_row))
        values = values[:10]
        if not any(str(value).strip() for value in values):
            continue

        # Rows from the old schema have numeric activity_count and delay values
        # in columns D and F. Rows written by the current app have activity_count
        # and delay in columns E and G, even when their header was stale.
        if _is_number(values[3]) and _is_number(values[5]):
            normalized_rows.append(
                [
                    values[0],
                    values[1],
                    values[2],
                    "",
                    values[3],
                    values[4],
                    values[5],
                    values[6],
                    values[7],
                    values[8],
                ]
            )
        else:
            normalized_rows.append(values)

    worksheet.update(
        range_name=f"A1:J{len(normalized_rows)}",
        values=normalized_rows,
        value_input_option="USER_ENTERED",
    )


def _is_number(value: str) -> bool:
    try:
        float(str(value).strip())
        return True
    except (TypeError, ValueError):
        return False


def _minutes_series(values: pd.Series) -> pd.Series:
    # Google Sheets can return numeric cells as strings, or as display text
    # such as "20 mins". Extract the numeric portion before summing.
    numeric_values = values.astype("string").str.replace(",", "", regex=False).str.extract(
        r"([-+]?\d+(?:\.\d+)?)", expand=False
    )
    return pd.to_numeric(numeric_values, errors="coerce").fillna(0)


def reset_form() -> None:
    st.session_state.selected_staff = None
    st.session_state.form_version = st.session_state.get("form_version", 0) + 1


@st.fragment
def render_activity_selector(version: int) -> None:
    """Render the activity controls without rerunning the rest of the app."""
    selected_activity = st.selectbox(
        "**Activity**",
        options=ACTIVITY_OPTIONS,
        index=None,
        placeholder="Choose an activity or Select 'Other' and describe your own.",
        accept_new_options=True,
        help=FIELD_HELP["target_activity"],
        key=f"target_activity_{version}",
    )
    if selected_activity == "Other":
        activity_value = st.text_input(
            "**Describe the other activity**",
            placeholder="Describe the activity",
            help="Add a short description so this entry can be understood later.",
            key=f"other_activity_{version}",
        )
    else:
        activity_value = selected_activity or ""

    st.session_state[f"selected_activity_{version}"] = selected_activity
    st.session_state[f"activity_value_{version}"] = activity_value


if "selected_staff" not in st.session_state:
    st.session_state.selected_staff = None
if "form_version" not in st.session_state:
    st.session_state.form_version = 0
if "show_entries" not in st.session_state:
    st.session_state.show_entries = False

log_df = read_log()
delay_minutes = _minutes_series(log_df["delay_minutes"])

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
    "Breaks recorded",
    f"{(log_df['entry_type'] == 'Break').sum()}",
)
st.sidebar.metric(
    "Total delay time identified",
    f"{int(delay_minutes.sum())} mins",
)
st.sidebar.divider()
st.sidebar.markdown("**Google Sheet**")
st.sidebar.caption("Uses the private `gsheets` connection from `.streamlit/secrets.toml`.")
st.sidebar.link_button(
    "Open Google Sheet",
    GOOGLE_SHEET_URL,
    icon=":material/table_view:",
    width="stretch",
)
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
                "friction_point": "Friction point",
                "delay_minutes": "Delay minutes",
                "suggested_improvement": "Suggested improvement",
                "break_type": "Break type",
                "break_note": "Break note",
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

            .moving-line.line-two {
                animation-duration: 23s;
                animation-delay: -8s;
                background: rgba(236, 93, 75, 0.22);
                left: 9%;
                top: 62%;
                width: 82%;
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
                color: #ffffff;
                font-size: clamp(2rem, 5vw, 3.8rem);
                font-weight: 900;
                line-height: 1.05;
                margin: 0;
                min-height: 2.9em;
                padding-bottom: 0.15em;
            }

            .message-stage {
                box-sizing: border-box;
                display: grid;
                height: auto;
                min-height: 2.9em;
                overflow: visible;
                padding-bottom: 0;
                position: relative;
            }

            .hero-message {
                animation-duration: 18s;
                animation-iteration-count: infinite;
                animation-timing-function: ease-in-out;
                display: block;
                grid-area: 1 / 1;
                position: relative;
                width: 100%;
                white-space: normal;
            }

            .hero-message-title {
                animation-name: message-title;
            }

            .hero-message-activity {
                animation-name: message-activity;
            }

            .hero-message-break {
                animation-name: message-break;
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

            @keyframes message-title {
                0%, 56%, 100% {
                    opacity: 0;
                    transform: translateY(14px) scale(0.94);
                    filter: blur(7px);
                }
                5%, 48% {
                    opacity: 1;
                    transform: translateY(0) scale(1);
                    filter: blur(0);
                }
            }

            @keyframes message-activity {
                0%, 52%, 100% {
                    opacity: 0;
                    transform: translateX(-24px) rotate(-2deg);
                    filter: blur(5px);
                }
                58%, 71% {
                    opacity: 1;
                    transform: translateX(0) rotate(0);
                    filter: blur(0);
                }
                78% {
                    opacity: 0;
                    transform: translateX(24px) rotate(2deg);
                    filter: blur(5px);
                }
            }

            @keyframes message-break {
                0%, 74%, 100% {
                    opacity: 0;
                    transform: translateY(-16px) scale(1.12) rotate(5deg);
                    filter: blur(6px);
                }
                82%, 94% {
                    opacity: 1;
                    transform: translateY(0) scale(1) rotate(0);
                    filter: blur(0);
                }
                100% {
                    opacity: 0;
                    transform: translateY(16px) scale(0.92) rotate(-3deg);
                    filter: blur(6px);
                }
            }

            @media (prefers-reduced-motion: reduce) {
                .hero-message {
                    animation: none;
                }

                .hero-message-title {
                    opacity: 1;
                    position: relative;
                }

                .hero-message-activity,
                .hero-message-break {
                    display: none;
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
            <span class="moving-line line-two"></span>
        </div>
        <div class="main-title-banner">
            <p class="main-title-kicker">Workflow Intelligence</p>
            <h1 class="main-title-text" aria-live="polite">
                <span class="message-stage">
                    <span class="hero-message hero-message-title">Activity / Friction Log</span>
                    <span class="hero-message hero-message-activity">Remember to log each new activity</span>
                    <span class="hero-message hero-message-break">End of day - record Break (End of day)</span>
                </span>
            </h1>
        </div>
        """
    )
    render_staff_statuses(log_df)



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
    now = datetime.now(LONDON_TZ).isoformat(timespec="seconds")
    version = st.session_state.form_version

    st.subheader(f":shimmer[Entry for {staff_member}]")
    entry_type = st.segmented_control(
        "What are you recording?",
        options=ENTRY_TYPES,
        default=ENTRY_TYPES[0],
        key=f"entry_type_{version}",
    )
    if entry_type == "Break":
        selected_activity = None
        target_activity = ""
    else:
        render_activity_selector(version)
        selected_activity = st.session_state.get(f"selected_activity_{version}")
        target_activity = st.session_state.get(f"activity_value_{version}", "")

    with st.form(f"friction_form_{version}", clear_on_submit=True, border=False):
        # st.text_input("Date & Time", value=now, disabled=True)
        st.markdown(f":material/date_range:`{now}`")
        st.caption(FIELD_HELP["recorded_at"])
        if entry_type == "Break":
            target_activity = ""
        if entry_type == "Work activity":
            activity_count = st.number_input(
                "**Number completed**",
                min_value=1,
                value=1,
                step=1,
                help=FIELD_HELP["activity_count"],
                key=f"activity_count_{version}",
            )
            friction_point = ""
            delay = 0
            suggested_improvement = ""
            break_type = ""
            break_minutes = 0
            break_note = ""
        elif entry_type == "Friction point":
            activity_count = 1
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
            break_type = ""
            break_minutes = 0
            break_note = ""
        else:
            activity_count = 0
            minutes_spent = 0
            break_type = st.selectbox(
                "**Break type**",
                options=BREAK_TYPES,
                help="Choose the kind of break you are recording.",
                key=f"break_type_{version}",
            )
            break_note = st.text_area(
                "**Note (optional)**",
                placeholder="Stepped away for a quick reset.",
                help=FIELD_HELP["break_note"],
                key=f"break_note_{version}",
            )
            friction_point = ""
            delay = 0
            suggested_improvement = ""

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
                **(
                    {
                        "Other activity"
                        if selected_activity == "Other"
                        else "Activity": target_activity
                    }
                    if entry_type != "Break"
                    else {}
                ),
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
                        "friction_point": friction_point.strip(),
                        "delay_minutes": int(delay),
                        "suggested_improvement": suggested_improvement.strip(),
                        "break_type": break_type,
                        "break_note": break_note.strip(),
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
