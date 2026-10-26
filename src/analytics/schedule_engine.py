"""
Deterministic Schedule Variance & Critical Path Analysis Engine.
Calculates planned vs actual dates, duration variance, overdue milestones,
progress slippage, and critical path impact against a verifiable cutoff date.
"""

from datetime import datetime, date
from typing import Dict, Any, List, Optional
import pandas as pd
import numpy as np

from config.settings import DEFAULT_CUTOFF_DATE, CRITICAL_FLOAT_THRESHOLD_DAYS


class ScheduleEngine:
    """
    Deterministic schedule analysis engine for infrastructure activities.
    Follows strict scheduling rules: distinguishes completed from in-progress,
    calculates overdue status using cutoff dates, and avoids unsupported CPM claims.
    """

    def __init__(self, activities_df: pd.DataFrame, dependencies_df: Optional[pd.DataFrame] = None, cutoff_date: Optional[date] = None):
        self.raw_df = activities_df.copy()
        self.dep_df = dependencies_df.copy() if dependencies_df is not None else pd.DataFrame()
        self.cutoff_date = cutoff_date if cutoff_date else DEFAULT_CUTOFF_DATE
        self.cutoff_dt = pd.to_datetime(self.cutoff_date)
        self.processed_df = pd.DataFrame()

    def analyze(self) -> pd.DataFrame:
        """
        Executes deterministic schedule calculations on all activities.
        Returns enriched DataFrame with delay days, overdue flags, and float indicators.
        """
        if self.raw_df.empty:
            return pd.DataFrame()

        df = self.raw_df.copy()

        # Ensure datetime formats
        for c in ["planned_start", "planned_finish", "actual_start", "actual_finish"]:
            if c in df.columns:
                df[c] = pd.to_datetime(df[c], errors="coerce")

        # 1. Planned and Actual Durations (working/calendar days based on dataset)
        df["planned_duration_calc"] = (df["planned_finish"] - df["planned_start"]).dt.days
        df["actual_duration_calc"] = (df["actual_finish"] - df["actual_start"]).dt.days

        # 2. Activity Status Classification
        df["is_completed"] = (df["status"] == "COMPLETED") | (df["actual_finish"].notnull())
        df["is_in_progress"] = (df["status"] == "IN_PROGRESS") & (~df["is_completed"])
        df["is_not_started"] = (df["status"] == "NOT_STARTED") & (~df["is_completed"])

        # 3. Delay Calculations for Completed Activities
        # Finish-date delay = actual_finish - planned_finish
        df["finish_delay_days"] = np.where(
            df["is_completed"] & df["actual_finish"].notnull() & df["planned_finish"].notnull(),
            (df["actual_finish"] - df["planned_finish"]).dt.days,
            np.nan
        )

        # 4. Overdue and Start Delay for Incomplete Activities
        # If incomplete and planned_finish is before the cutoff date, activity is overdue
        df["is_overdue"] = np.where(
            (~df["is_completed"]) & (df["planned_finish"] < self.cutoff_dt),
            True,
            False
        )

        df["overdue_days"] = np.where(
            df["is_overdue"],
            (self.cutoff_dt - df["planned_finish"]).dt.days,
            0
        )

        # Start delay for in-progress or late-start activities
        df["start_delay_days"] = np.where(
            df["actual_start"].notnull() & df["planned_start"].notnull(),
            (df["actual_start"] - df["planned_start"]).dt.days,
            np.where(
                df["is_not_started"] & (df["planned_start"] < self.cutoff_dt),
                (self.cutoff_dt - df["planned_start"]).dt.days,
                0
            )
        )

        # Progress slippage: positive means actual progress is lagging planned progress
        df["progress_slippage_pct"] = np.where(
            df["planned_progress_pct"].notnull() & df["actual_progress_pct"].notnull(),
            df["planned_progress_pct"] - df["actual_progress_pct"],
            0.0
        )

        # 5. Effective Delay Days (Unified observed delay metric)
        df["delay_days"] = np.where(
            df["is_completed"],
            df["finish_delay_days"].fillna(0),
            np.where(
                df["is_overdue"],
                df["overdue_days"],
                np.maximum(0, df["start_delay_days"])
            )
        ).astype(int)

        # 6. Critical Path & Milestone Impact
        # Activity affects critical path if marked critical (or float <= 0) and has positive delay
        df["critical_float"] = df["total_float_days"].fillna(0) <= CRITICAL_FLOAT_THRESHOLD_DAYS
        df["is_critical_effective"] = df["is_critical"] | df["critical_float"]

        df["critical_path_impact"] = df["is_critical_effective"] & (df["delay_days"] > 0)
        df["milestone_delayed"] = df["is_milestone"] & (df["delay_days"] > 0)

        # 7. Delay Categorization
        conditions = [
            (df["delay_days"] <= 0),
            (df["delay_days"] > 0) & (df["delay_days"] <= 5),
            (df["delay_days"] > 5) & (df["delay_days"] <= 15),
            (df["delay_days"] > 15)
        ]
        choices = ["ON_TIME", "LOW_DELAY", "MEDIUM_DELAY", "CRITICAL_DELAY"]
        df["delay_category"] = np.select(conditions, choices, default="ON_TIME")

        self.processed_df = df
        return df

    def get_kpis(self, project_id: Optional[str] = None) -> Dict[str, Any]:
        """Calculates project-level or portfolio-level schedule KPI metrics."""
        if self.processed_df.empty:
            self.analyze()

        df = self.processed_df
        if project_id:
            df = df[df["project_id"] == project_id]

        total = len(df)
        if total == 0:
            return {"total_activities": 0, "status": "Insufficient data"}

        completed = int(df["is_completed"].sum())
        in_progress = int(df["is_in_progress"].sum())
        not_started = int(df["is_not_started"].sum())
        delayed = int((df["delay_days"] > 0).sum())
        overdue = int(df["is_overdue"].sum())
        crit_delayed = int(df["critical_path_impact"].sum())
        ms_delayed = int(df["milestone_delayed"].sum())

        avg_delay = float(df[df["delay_days"] > 0]["delay_days"].mean()) if delayed > 0 else 0.0
        max_delay = int(df["delay_days"].max()) if delayed > 0 else 0

        return {
            "total_activities": total,
            "completed_activities": completed,
            "in_progress_activities": in_progress,
            "not_started_activities": not_started,
            "delayed_activities": delayed,
            "overdue_activities": overdue,
            "critical_activities_delayed": crit_delayed,
            "milestones_delayed": ms_delayed,
            "delayed_pct": round(delayed / total * 100, 1),
            "average_delay_days": round(avg_delay, 1),
            "maximum_delay_days": max_delay,
            "cutoff_date": str(self.cutoff_date)
        }

    def get_successors(self, activity_id: str) -> List[Dict[str, Any]]:
        """Returns direct successor activities affected by this activity."""
        if self.dep_df.empty or "predecessor_activity_id" not in self.dep_df.columns:
            return []

        succs = self.dep_df[self.dep_df["predecessor_activity_id"] == activity_id]
        if succs.empty:
            return []

        results = []
        for _, row in succs.iterrows():
            succ_id = row["successor_activity_id"]
            # Look up successor details if available
            succ_info = {"activity_id": succ_id, "relationship": row.get("relationship_type", "FS"), "lag_days": row.get("lag_days", 0)}
            if not self.processed_df.empty:
                match = self.processed_df[self.processed_df["activity_id"] == succ_id]
                if not match.empty:
                    succ_info["activity_name"] = match.iloc[0]["activity_name"]
                    succ_info["is_critical"] = bool(match.iloc[0]["is_critical_effective"])
                    succ_info["status"] = match.iloc[0]["status"]
            results.append(succ_info)
        return results
