from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd


CSV_PATH = Path("/Users/janduplessis/Downloads/friction-log - Sheet1 (1).csv")
OUTPUT_PATH = Path("friction_log_analysis.png")


def load_and_normalize(path: Path) -> pd.DataFrame:
    # The export contains two row layouts: older rows have no task-name field;
    # newer rows put task name before activity_count. Detect them by type.
    raw = pd.read_csv(path, header=None, skiprows=1, dtype=str).fillna("")
    rows = []
    for _, row in raw.iterrows():
        values = row.tolist()
        entry_type = values[2].strip()
        if values[3].strip().replace(".", "", 1).isdigit():
            task = "Unnamed work activity" if entry_type == "Work activity" else ""
            activity_count = values[3].strip()
            friction_point, delay, improvement = values[4].strip(), values[5].strip(), values[6].strip()
            break_type, break_note = values[7].strip(), values[8].strip()
        else:
            task = values[3].strip()
            activity_count = values[4].strip()
            friction_point, delay, improvement = values[5].strip(), values[6].strip(), values[7].strip()
            break_type, break_note = values[8].strip(), values[9].strip()
        rows.append(
            {
                "recorded_at_serial": values[0].strip(),
                "staff_member": values[1].strip(),
                "entry_type": entry_type,
                "task": task,
                "activity_count": pd.to_numeric(activity_count, errors="coerce"),
                "friction_point": friction_point,
                "delay_minutes": pd.to_numeric(delay, errors="coerce").fillna(0) if hasattr(pd.to_numeric(delay, errors="coerce"), "fillna") else float(delay or 0),
                "break_type": break_type,
                "break_note": break_note,
            }
        )
    df = pd.DataFrame(rows)
    df["recorded_at"] = pd.to_datetime(
        pd.to_numeric(df["recorded_at_serial"], errors="coerce"), unit="D", origin="1899-12-30"
    )
    return df.sort_values("recorded_at").reset_index(drop=True)


def main() -> None:
    df = load_and_normalize(CSV_PATH)
    df["estimated_minutes_to_next_entry"] = (
        df["recorded_at"].shift(-1).sub(df["recorded_at"]).dt.total_seconds().div(60)
    )
    # A gap is a proxy for time spent on the preceding entry, capped only for
    # display so an accidental long idle gap does not dominate the chart.
    named = df[(df["entry_type"] == "Work activity") & (df["task"] != "Unnamed work activity")].copy()
    named = named[named["estimated_minutes_to_next_entry"].notna()]
    named = named.sort_values("estimated_minutes_to_next_entry", ascending=True)

    plt.rcParams.update({"font.family": "DejaVu Sans", "axes.titleweight": "bold"})
    fig = plt.figure(figsize=(12, 8.2), facecolor="#fbfaf7")
    grid = fig.add_gridspec(2, 1, height_ratios=[1.15, 1], hspace=0.42)
    ax1 = fig.add_subplot(grid[0])
    ax2 = fig.add_subplot(grid[1])
    ink, muted, blue, coral, grid_color = "#17212b", "#65717b", "#2e6f95", "#d96c52", "#d9dedf"

    if not named.empty:
        labels = named["task"].str.slice(0, 34)
        bars = ax1.barh(labels, named["estimated_minutes_to_next_entry"], color=blue, alpha=0.9)
        for bar, value in zip(bars, named["estimated_minutes_to_next_entry"]):
            ax1.text(value + 0.15, bar.get_y() + bar.get_height() / 2, f"{value:.1f} min", va="center", fontsize=9, color=ink)
        ax1.set_xlim(0, max(named["estimated_minutes_to_next_entry"].max() * 1.25, 1))
    ax1.set_title("Estimated time associated with named tasks", loc="left", fontsize=15, color=ink, pad=12)
    ax1.text(0, 1.01, "Minutes from each task entry until the next recorded event; timestamp-gap proxy", transform=ax1.transAxes, color=muted, fontsize=9)
    ax1.set_xlabel("Estimated minutes", color=muted)
    ax1.grid(axis="x", color=grid_color, linewidth=0.8)
    ax1.set_axisbelow(True)
    ax1.spines[["top", "right", "left"]].set_visible(False)
    ax1.spines["bottom"].set_color(grid_color)
    ax1.tick_params(axis="y", length=0, colors=ink)
    ax1.tick_params(axis="x", colors=muted)

    # Timeline: activity counts and friction delay, showing how the day was logged.
    work = df[df["entry_type"].isin(["Work activity", "Friction point"])].copy()
    ax2.scatter(work["recorded_at"], work["activity_count"].fillna(0), s=65, color=blue, label="Activity count", zorder=3)
    friction = df[df["entry_type"] == "Friction point"]
    if not friction.empty:
        ax2.scatter(friction["recorded_at"], friction["activity_count"].fillna(0), s=120, marker="D", color=coral, label="Friction point", zorder=4)
        for _, row in friction.iterrows():
            ax2.annotate(f"{int(row['delay_minutes'])} min delay", (row["recorded_at"], row["activity_count"]), xytext=(8, 10), textcoords="offset points", color=coral, fontsize=9)
    ax2.set_title("Logged activity volume across the recording period", loc="left", fontsize=15, color=ink, pad=12)
    ax2.text(0, 1.01, "Work entries are blue; the recorded friction point is highlighted in coral", transform=ax2.transAxes, color=muted, fontsize=9)
    ax2.set_ylabel("Activity count", color=muted)
    ax2.set_xlabel("Recorded time", color=muted)
    ax2.grid(axis="y", color=grid_color, linewidth=0.8)
    ax2.set_axisbelow(True)
    ax2.spines[["top", "right", "left"]].set_visible(False)
    ax2.spines["bottom"].set_color(grid_color)
    ax2.tick_params(colors=muted)
    ax2.legend(frameon=False, loc="upper left")

    fig.suptitle("Friction log: task time and activity overview", x=0.08, ha="left", fontsize=20, color=ink, weight="bold")
    fig.text(0.08, 0.015, f"Source: {CSV_PATH.name}  •  {len(df)} entries  •  {df['recorded_at'].min():%d %b %Y}  •  durations are estimated from adjacent timestamps", fontsize=8.5, color=muted)
    fig.subplots_adjust(top=0.88, bottom=0.08, left=0.22, right=0.96)
    fig.savefig(OUTPUT_PATH, dpi=180, facecolor=fig.get_facecolor())
    print(f"Saved {OUTPUT_PATH.resolve()}")
    print(f"Entries: {len(df)}; named tasks: {len(named)}; total recorded delay: {df['delay_minutes'].sum():.0f} minutes")
    if not named.empty:
        print(named[["task", "estimated_minutes_to_next_entry"]].to_string(index=False))


if __name__ == "__main__":
    main()
