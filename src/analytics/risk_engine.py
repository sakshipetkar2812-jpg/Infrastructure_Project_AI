"""
Risk Classification and Delay/Cost Impact Forecasting Engine.
Implements transparent multi-factor risk scoring, explainable baseline delay/cost projections,
and statistical predictive models evaluated on historical project activities.
"""

from typing import Dict, Any, List, Optional, Tuple
import pandas as pd
import numpy as np
from sklearn.linear_model import LogisticRegression, Ridge
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, mean_absolute_error

from config.settings import (
    CRITICAL_FLOAT_THRESHOLD_DAYS,
    DELAY_LOW_THRESHOLD_DAYS,
    DELAY_HIGH_THRESHOLD_DAYS,
    COST_OVERRUN_ALERT_PCT
)


class RiskAndForecastingEngine:
    """
    Evaluates multi-factor risk classifications and computes defensible schedule/cost forecasts.
    Explicitly separates observed delay from predicted delay.
    """

    def __init__(
        self,
        analyzed_activities_df: pd.DataFrame,
        contractors_df: Optional[pd.DataFrame] = None
    ):
        self.activities_df = analyzed_activities_df.copy()
        self.contractors_df = contractors_df.copy() if contractors_df is not None else pd.DataFrame()
        self.ml_classifier = None
        self.ml_accuracy = 0.0
        self.is_trained = False

    def calculate_activity_risk_score(self, activity_row: pd.Series, procurement_status: Optional[Dict[str, Any]] = None, contractor_status: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Computes a transparent, multi-factor risk score (0-100) and risk level.
        Documents the exact points contribution from each risk dimension.
        """
        score = 0.0
        breakdown = {}

        # 1. Schedule Delay & Overdue (Up to 30 points)
        delay_days = int(activity_row.get("delay_days", 0))
        is_overdue = bool(activity_row.get("is_overdue", False))
        if delay_days > DELAY_HIGH_THRESHOLD_DAYS or (is_overdue and delay_days > 10):
            sched_pts = 30.0
        elif delay_days > DELAY_LOW_THRESHOLD_DAYS:
            sched_pts = 18.0
        elif delay_days > 0:
            sched_pts = 8.0
        else:
            sched_pts = 0.0
        score += sched_pts
        breakdown["schedule_delay_points"] = sched_pts

        # 2. Critical Path Exposure (Up to 25 points)
        is_critical = bool(activity_row.get("is_critical_effective", False))
        if is_critical and delay_days > 0:
            crit_pts = 25.0
        elif is_critical:
            crit_pts = 10.0
        else:
            crit_pts = 0.0
        score += crit_pts
        breakdown["critical_path_points"] = crit_pts

        # 3. Material Supply & Inventory Deficit (Up to 15 points)
        mat_pts = 0.0
        if procurement_status:
            if procurement_status.get("has_shortage"):
                mat_pts += 10.0
            if procurement_status.get("has_delivery_defect"):
                mat_pts += 5.0
        score += mat_pts
        breakdown["procurement_risk_points"] = mat_pts

        # 4. Contractor & Labor Productivity Deficit (Up to 15 points)
        lab_pts = 0.0
        if contractor_status:
            if contractor_status.get("has_productivity_deficit"):
                lab_pts += 10.0
            if contractor_status.get("has_contractor_risk"):
                lab_pts += 5.0
        score += lab_pts
        breakdown["labor_productivity_points"] = lab_pts

        # 5. Cost Overrun Variance (Up to 15 points)
        baseline = float(activity_row.get("baseline_cost", 0))
        actual = float(activity_row.get("actual_cost", 0))
        variance_pct = ((actual - baseline) / baseline * 100) if baseline > 0 else 0.0
        if variance_pct > COST_OVERRUN_ALERT_PCT * 2:
            cost_pts = 15.0
        elif variance_pct > COST_OVERRUN_ALERT_PCT:
            cost_pts = 8.0
        elif variance_pct > 0:
            cost_pts = 3.0
        else:
            cost_pts = 0.0
        score += cost_pts
        breakdown["cost_overrun_points"] = cost_pts

        # Risk Classification
        total_score = min(100.0, round(score, 1))
        if total_score >= 70.0:
            level = "CRITICAL"
        elif total_score >= 45.0:
            level = "HIGH"
        elif total_score >= 25.0:
            level = "MEDIUM"
        else:
            level = "LOW"

        return {
            "risk_score": total_score,
            "risk_level": level,
            "scoring_breakdown": breakdown,
            "is_critical_path": is_critical,
            "delay_days": delay_days,
            "cost_variance_pct": round(variance_pct, 2)
        }

    def forecast_completion_and_cost(self, activity_row: pd.Series) -> Dict[str, Any]:
        """
        Transparent baseline forecast of completion date and final expected cost.
        Clearly documents assumptions, formula, and uncertainty.
        """
        planned_dur = max(1, float(activity_row.get("planned_duration_calc", 1) or 1))
        actual_progress = float(activity_row.get("actual_progress_pct", 0) or 0)
        baseline_cost = float(activity_row.get("baseline_cost", 0))
        actual_cost = float(activity_row.get("actual_cost", 0))
        is_completed = bool(activity_row.get("is_completed", False))

        if is_completed:
            return {
                "forecast_type": "ACTUAL_COMPLETED",
                "predicted_total_duration_days": float(activity_row.get("actual_duration_calc", planned_dur)),
                "predicted_final_cost": actual_cost,
                "projected_cost_variance": round(actual_cost - baseline_cost, 2),
                "assumptions": "Activity already completed. Actual records used."
            }

        # For incomplete activities:
        # Progress-based Earned Value extrapolation
        if actual_progress > 5.0:
            # Earned value Cost Performance Index (CPI) and Schedule Performance Index (SPI)
            planned_progress = max(1.0, float(activity_row.get("planned_progress_pct", 100) or 100))
            spi = actual_progress / planned_progress
            cpi = (actual_progress / 100.0 * baseline_cost) / max(1.0, actual_cost)

            est_duration = planned_dur / max(0.2, spi)
            est_cost = baseline_cost / max(0.2, cpi)
            method = "Earned Value Standard Extrapolation (SPI / CPI)"
        else:
            # Insufficient progress for reliable EVM extrapolation: use baseline duration + observed delay
            delay_days = float(activity_row.get("delay_days", 0))
            est_duration = planned_dur + delay_days
            est_cost = baseline_cost * 1.05  # 5% contingency assumption
            method = "Baseline Schedule Extension with Contingency (Early Stage Activity)"

        return {
            "forecast_type": "PREDICTIVE_FORECAST",
            "predicted_total_duration_days": round(est_duration, 1),
            "predicted_final_cost": round(est_cost, 2),
            "projected_cost_variance": round(est_cost - baseline_cost, 2),
            "forecasting_method": method,
            "assumptions": "Assumes current progress execution rate continues to completion without intervention."
        }

    def train_baseline_ml_model(self) -> Dict[str, Any]:
        """
        Trains an explainable Machine Learning model on historical completed activities
        to predict delay risk probability based on activity scope, duration, and baseline cost.
        """
        df = self.activities_df
        if df.empty:
            return {"status": "No data available"}

        completed = df[df["is_completed"]].copy()
        if len(completed) < 100:
            return {"status": "Insufficient completed activities for robust ML training"}

        # Define target: Will the activity suffer delay > 5 days?
        completed["target_delayed"] = (completed["delay_days"] > 5).astype(int)

        # Feature matrix
        features = ["planned_duration_calc", "baseline_cost", "is_milestone", "is_critical_effective"]
        X = completed[features].copy()
        X = X.fillna(0)
        y = completed["target_delayed"]

        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.25, random_state=42)

        clf = LogisticRegression(max_iter=1000)
        clf.fit(X_train, y_train)

        preds = clf.predict(X_test)
        acc = round(accuracy_score(y_test, preds) * 100, 2)

        self.ml_classifier = clf
        self.ml_accuracy = acc
        self.is_trained = True

        return {
            "status": "Model successfully trained",
            "model_type": "Logistic Regression Baseline Classifier",
            "training_samples": len(X_train),
            "testing_samples": len(X_test),
            "test_accuracy_pct": acc,
            "target": "Activity delay exceeding 5 days",
            "features_used": features
        }
