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
    "Ceylon",

]

COLUMNS = [
    "recorded_at",
    "staff_member",
    "target_activity",
    "friction_point",
    "delay_minutes",
    "suggested_improvement",
]

BUTTON_ROW_PATTERN = [4, 3]


st.set_page_config(
    page_title="Friction Log",
    page_icon="",
    layout="centered",
)
st.logo("logo.png", size="large")

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

    return data[COLUMNS]


def append_log_entry(entry: dict) -> None:
    conn = st.connection("gsheets", type=GSheetsConnection)
    existing = read_log()
    updated = pd.concat([existing, pd.DataFrame([entry])], ignore_index=True)
    conn.update(data=updated)
    read_log.clear()


def reset_form() -> None:
    st.session_state.selected_staff = None
    st.session_state.form_version = st.session_state.get("form_version", 0) + 1


if "selected_staff" not in st.session_state:
    st.session_state.selected_staff = None
if "form_version" not in st.session_state:
    st.session_state.form_version = 0

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
    "Friction points recorded",
    f"{len(log_df)} points",
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

if not st.session_state.selected_staff:
    st.html(
        """
        <style>
            .main-title-banner {
                animation: banner-rise 520ms ease-out both, banner-glow 7s ease-in-out infinite;
                background: linear-gradient(105deg, #101c28 0%, #101c28 48%, #344451 68%, #101c28 100%);
                background-size: 180% 180%;
                border: 1px solid transparent;
                border-radius: 10px;
                box-shadow: 0 26px 42px rgba(12, 23, 34, 0.14);
                color: #ffffff;
                margin-bottom: 1.6rem;
                padding: 2rem 2rem;
                transition: border-color 140ms ease, box-shadow 140ms ease, transform 140ms ease;
            }

            .main-title-banner:hover {
                border-color: #ec5d4b;
                box-shadow: 0 30px 48px rgba(12, 23, 34, 0.18);
                transform: translateY(-1px);
            }

            .main-title-kicker {
                color: rgba(255, 255, 255, 0.82);
                font-size: 0.95rem;
                font-weight: 700;
                letter-spacing: 0.12em;
                margin: 0 0 0.7rem;
                text-transform: uppercase;
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
        </style>
        <div class="main-title-banner">
            <p class="main-title-kicker">Workflow Intelligence</p>
            <h1 class="main-title-text">Friction Log</h1>
        </div>
        """
    )



if not st.session_state.selected_staff:
    st.space(40)
    row_start = 0
    row_index = 0
    while row_start < len(STAFF_MEMBERS):
        buttons_in_row = BUTTON_ROW_PATTERN[row_index % len(BUTTON_ROW_PATTERN)]
        row_members = STAFF_MEMBERS[row_start : row_start + buttons_in_row]
        row = st.columns(buttons_in_row)
        for column, member in zip(row, row_members):
            with column:
                if st.button(member, type="primary", width="stretch", icon=":material/person:"):
                    st.session_state.selected_staff = member
                    st.rerun()
        row_start += buttons_in_row
        row_index += 1
        if row_start < len(STAFF_MEMBERS):
            st.space(1)

if st.session_state.selected_staff:
    staff_member = st.session_state.selected_staff
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    version = st.session_state.form_version

    st.subheader(f":shimmer[Entry for {staff_member}]")
    with st.form(f"friction_form_{version}", clear_on_submit=True):
        # st.text_input("Date & Time", value=now, disabled=True)
        st.markdown(f":material/date_range:`{now}`")
        target_activity = st.text_area(
            "Target Activity",
            placeholder="Filing DEXA scans",
            key=f"target_activity_{version}",
        )
        friction_point = st.text_area(
            "Obstacle / Friction Point",
            placeholder="System auto-attached 3 patient files together",
            key=f"friction_point_{version}",
        )
        delay = st.selectbox(
            "Delay Time",
            options=list(range(0, 125, 5)),
            format_func=lambda minutes: f"{minutes} mins",
            index=3,
            key=f"delay_{version}",
        )
        suggested_improvement = st.text_area(
            "Suggested Improvement",
            placeholder="Seperate pages in document management before filling.",
            key=f"suggested_improvement_{version}",
        )

        submitted = st.form_submit_button(
            "Submit friction point",
            type="primary",
            use_container_width=True,
        )

    cancel = st.button("Cancel entry", use_container_width=True)

    if cancel:
        reset_form()
        st.rerun()

    if submitted:
        missing_fields = [
            label
            for label, value in {
                "Target Activity": target_activity,
                "Obstacle / Friction Point": friction_point,
                "Suggested Improvement": suggested_improvement,
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
                        "target_activity": target_activity.strip(),
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
                st.success("Friction point recorded.")
                reset_form()
                st.rerun()
