# Activity / Friction Log

A Streamlit application for recording staff work activities, friction points, and breaks, then analysing how time is distributed across activities and users.

## What the app does

The app has two views:

- **Log an entry** (`streamlit_app.py`) lets a staff member choose their name and record a work activity, friction point, or break.
- **Activity dashboard** (`pages/activity.py`) reads the shared Google Sheet and provides filtered analysis by staff member and date range.

The sidebar also includes a button to open the connected [Google Sheet](https://docs.google.com/spreadsheets/d/1SJsxuSaTb0kM5iIpCm82Jyy09Vpu19UX_Rkbe1uNWIs/edit?usp=sharing).

## Data captured

Each row contains:

| Field | Purpose |
| --- | --- |
| `recorded_at` | London-time timestamp when the entry was submitted |
| `staff_member` | Person recording the entry |
| `entry_type` | `Work activity`, `Friction point`, or `Break` |
| `target_activity` | Selected activity category or custom activity |
| `activity_count` | Number of units completed |
| `friction_point` | Description of the obstacle, when applicable |
| `delay_minutes` | Estimated delay caused by friction |
| `suggested_improvement` | Proposed process or system improvement |
| `break_type` | Type of break, when applicable |
| `break_note` | Optional break context or comment |

New entries are appended to the Google Sheet as individual rows. The app only rewrites the sheet when it detects that the sheet headers or legacy layout need migration.

## Dashboard analysis

The dashboard uses the selected staff and date filters for its calculations.

### Summary KPIs

The main dashboard shows:

- Work units completed
- Number of work entries
- Number of friction points
- Number of breaks

### Time spent per activity

The Gantt chart estimates the duration of an entry as the time between that entry and the next entry recorded by the same user.

Only spans that meet all of these conditions are included:

- The entry is a work activity or break.
- A following entry exists for the same user.
- Both timestamps fall on the same day.
- The estimated duration is between 1 minute and 8 hours.

The Gantt chart can be filtered to a selected staff member. The table below it groups the selected user's entries by activity and shows:

- Total time in minutes and hours
- Total units completed
- Average estimated minutes per unit
- A sparkline showing the per-entry minutes per unit for that activity

Breaks have time estimates but no units, so their per-unit values are blank.

### User analysis

The user analysis section contains two dataframes.

The first provides one row per user:

- **Median time per unit:** the typical minutes needed to complete one unit. Lower values generally indicate faster throughput.
- **Estimated work time:** total inferred work time from valid timestamp gaps. This is an estimate rather than an exact stopwatch measurement.
- **Total units:** total recorded completed volume.
- **Context switches:** changes between consecutive work categories. Lower values may indicate fewer interruptions, although some roles naturally require more switching.
- **Consistency (CV %):** variation in time per unit relative to the average. Lower percentages indicate more consistent timings; higher percentages indicate greater variation.

The second dataframe shows time distribution by user and activity:

- **Time (min):** estimated minutes spent on the activity.
- **Time distribution (%):** that activity's share of the user's estimated work time.

### Daily trends and activity

This section contains two charts:

- **Daily trend:** estimated work time in minutes for each user by day. Sustained patterns and unusual spikes are more useful than interpreting a single day in isolation.
- **Daily activity:** completed units for each user by day. Comparing this with the time trend helps distinguish higher workload from slower throughput.

### Entries by staff member

This chart remains visible on the main dashboard and shows the number of recorded entries by user and entry type.

## Important interpretation notes

The duration analysis is a timestamp-gap proxy. It assumes the user was working on the preceding entry until their next entry, which means the estimate can include idle time, interruptions, meetings, or unlogged work.

Time per unit is most useful when comparing similar work. Activities with different levels of complexity should not be compared without additional context.

The dashboard currently does not capture exact start and end times, task complexity, waiting time, rework, or whether a task was completed successfully. Those fields would improve future analysis.

## Setup

1. Create or activate a Python environment.
2. Install the dependencies:

   ```bash
   pip install -r requirements.txt
   ```

3. Configure the private `gsheets` connection in `.streamlit/secrets.toml` using the `streamlit-gsheets-connection` documentation.
4. Grant the configured Google service account access to the spreadsheet.
5. Start the app:

   ```bash
   streamlit run streamlit_app.py
   ```

If the Google Sheets connection is unavailable, the app falls back to an empty log for display and reports the connection error when a new entry cannot be saved.

The Activity dashboard is PIN-protected. The PIN is configured in `pages/activity.py`; change it before deploying the app.

## Project structure

```text
.
├── streamlit_app.py           # Entry form, Google Sheets writes, staff statuses
├── pages/activity.py          # PIN-protected dashboard and analysis
├── analyze_friction_log.py    # Standalone analysis script for a CSV export
├── friction_log_schema.csv    # Expected Google Sheet column order
├── requirements.txt            # Python dependencies
└── .streamlit/secrets.toml     # Local-only Google Sheets credentials
```

## Dependencies

- Streamlit
- `st-gsheets-connection`
- pandas
- Altair, provided through Streamlit's charting dependency stack
