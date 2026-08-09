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

FIELD_HELP = {
    "recorded_at": (
        ""
    ),
    "target_activity": (
        "Describe the task you were trying to complete. Keep it specific enough "
        "that someone else can understand the workflow, for example: scanning a "
        "referral, booking an appointment, or updating patient records."
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
    page_title="Friction Log",
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


def show_entry_list() -> None:
    st.session_state.show_entries = True
    st.session_state.selected_staff = None


def show_input_form() -> None:
    st.session_state.show_entries = False


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
st.sidebar.divider()
if st.session_state.show_entries:
    st.sidebar.button(
        "New entry",
        type="secondary",
        width="stretch",
        icon=":material/add:",
        on_click=show_input_form,
    )
else:
    st.sidebar.button(
        "View entries",
        type="secondary",
        width="stretch",
        icon=":material/table_view:",
        on_click=show_entry_list,
    )

if st.session_state.show_entries:
    st.subheader(":shimmer[Recorded entries]")
    if log_df.empty:
        st.info("No friction points recorded yet.")
    else:
        st.dataframe(log_df, width="stretch", hide_index=True)
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

            .floating-fl {
                animation: fl-drift-a 28s ease-in-out infinite;
                color: #b8bec5;
                font-size: 1.15rem;
                font-weight: 900;
                line-height: 1;
                opacity: 0.36;
                position: absolute;
                transform: translate3d(0, 0, 0) scale(var(--figure-scale, 1));
                user-select: none;
                white-space: nowrap;
            }

            .floating-fl:nth-child(1) { left: 8%; top: 12%; animation-duration: 31s; animation-delay: -7s; }
            .floating-fl:nth-child(2) { left: 18%; top: 74%; animation-delay: -13s; animation-duration: 24s; animation-name: fl-drift-b; --figure-scale: 0.78; }
            .floating-fl:nth-child(3) { left: 28%; top: 30%; animation-delay: -20s; animation-duration: 35s; animation-name: fl-drift-c; --figure-scale: 0.9; }
            .floating-fl:nth-child(4) { left: 36%; top: 88%; animation-delay: -3s; animation-duration: 27s; animation-name: fl-drift-b; --figure-scale: 0.72; }
            .floating-fl:nth-child(5) { left: 48%; top: 18%; animation-delay: -16s; animation-duration: 33s; animation-name: fl-drift-c; --figure-scale: 0.84; }
            .floating-fl:nth-child(6) { left: 57%; top: 64%; animation-delay: -22s; animation-duration: 29s; --figure-scale: 0.68; }
            .floating-fl:nth-child(7) { left: 67%; top: 36%; animation-delay: -11s; animation-duration: 26s; animation-name: fl-drift-b; --figure-scale: 0.82; }
            .floating-fl:nth-child(8) { left: 76%; top: 82%; animation-delay: -24s; animation-duration: 37s; animation-name: fl-drift-c; --figure-scale: 0.74; }
            .floating-fl:nth-child(9) { left: 86%; top: 22%; animation-delay: -5s; animation-duration: 30s; --figure-scale: 0.88; }
            .floating-fl:nth-child(10) { left: 94%; top: 58%; animation-delay: -18s; animation-duration: 34s; animation-name: fl-drift-b; --figure-scale: 0.7; }
            .floating-fl:nth-child(11) { left: 12%; top: 46%; animation-delay: -27s; animation-duration: 32s; animation-name: fl-drift-c; --figure-scale: 0.66; }
            .floating-fl:nth-child(12) { left: 42%; top: 52%; animation-delay: -9s; animation-duration: 25s; --figure-scale: 0.8; }
            .floating-fl:nth-child(13) { left: 72%; top: 8%; animation-delay: -15s; animation-duration: 36s; animation-name: fl-drift-b; --figure-scale: 0.62; }
            .floating-fl:nth-child(14) { left: 90%; top: 92%; animation-delay: -1s; animation-duration: 28s; animation-name: fl-drift-c; --figure-scale: 0.76; }

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

            @keyframes fl-drift-a {
                0% {
                    transform: translate3d(-8px, 0, 0) rotate(-7deg) scale(var(--figure-scale, 1));
                }
                25% {
                    transform: translate3d(24px, -32px, 0) rotate(6deg) scale(var(--figure-scale, 1));
                }
                50% {
                    transform: translate3d(58px, 8px, 0) rotate(-4deg) scale(var(--figure-scale, 1));
                }
                75% {
                    transform: translate3d(18px, 34px, 0) rotate(8deg) scale(var(--figure-scale, 1));
                }
                100% {
                    transform: translate3d(-8px, 0, 0) rotate(-7deg) scale(var(--figure-scale, 1));
                }
            }

            @keyframes fl-drift-b {
                0% {
                    transform: translate3d(0, 0, 0) rotate(8deg) scale(var(--figure-scale, 1));
                }
                30% {
                    transform: translate3d(-36px, 18px, 0) rotate(-5deg) scale(var(--figure-scale, 1));
                }
                60% {
                    transform: translate3d(18px, -42px, 0) rotate(10deg) scale(var(--figure-scale, 1));
                }
                100% {
                    transform: translate3d(0, 0, 0) rotate(8deg) scale(var(--figure-scale, 1));
                }
            }

            @keyframes fl-drift-c {
                0% {
                    transform: translate3d(0, 0, 0) rotate(-3deg) scale(var(--figure-scale, 1));
                }
                20% {
                    transform: translate3d(26px, 30px, 0) rotate(12deg) scale(var(--figure-scale, 1));
                }
                55% {
                    transform: translate3d(-28px, -18px, 0) rotate(-11deg) scale(var(--figure-scale, 1));
                }
                80% {
                    transform: translate3d(44px, -38px, 0) rotate(4deg) scale(var(--figure-scale, 1));
                }
                100% {
                    transform: translate3d(0, 0, 0) rotate(-3deg) scale(var(--figure-scale, 1));
                }
            }
        </style>
        <div class="main-animated-bg" aria-hidden="true">
            <span class="floating-fl">FL</span>
            <span class="floating-fl">FL</span>
            <span class="floating-fl">FL</span>
            <span class="floating-fl">FL</span>
            <span class="floating-fl">FL</span>
            <span class="floating-fl">FL</span>
            <span class="floating-fl">FL</span>
            <span class="floating-fl">FL</span>
            <span class="floating-fl">FL</span>
            <span class="floating-fl">FL</span>
            <span class="floating-fl">FL</span>
            <span class="floating-fl">FL</span>
            <span class="floating-fl">FL</span>
            <span class="floating-fl">FL</span>
        </div>
        <div class="main-title-banner">
            <p class="main-title-kicker">Workflow Intelligence</p>
            <h1 class="main-title-text">Friction Log</h1>
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
    with st.form(f"friction_form_{version}", clear_on_submit=True):
        # st.text_input("Date & Time", value=now, disabled=True)
        st.markdown(f":material/date_range:`{now}`")
        st.caption(FIELD_HELP["recorded_at"])
        target_activity = st.text_input(
            "**Target Activity**",
            placeholder="Multiple pts info in one pdf.",
            help=FIELD_HELP["target_activity"],
            key=f"target_activity_{version}",
        )
        friction_point = st.text_area(
            "**Obstacle / Friction Point**",
            placeholder="System auto-attached 3 patient files together",
            help=FIELD_HELP["friction_point"],
            key=f"friction_point_{version}",
        )
        delay = st.selectbox(
            "**Delay Time**",
            options=list(range(0, 125, 5)),
            format_func=lambda minutes: f"{minutes} mins",
            index=3,
            help=FIELD_HELP["delay_minutes"],
            key=f"delay_{version}",
        )
        suggested_improvement = st.text_area(
            "**Suggested Improvement**",
            placeholder="Separate pages in document management before filling.",
            help=FIELD_HELP["suggested_improvement"],
            key=f"suggested_improvement_{version}",
        )

        submitted = st.form_submit_button(
            "**Submit friction point**",
            type="primary",
            use_container_width=True,
            icon=":material/upload:",
        )

    cancel = st.button("Cancel entry", use_container_width=True, icon=":material/cancel:")

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
