"""
Deterministic Procurement & Material Shortage Analysis Engine.
Analyzes Bill of Quantities (BOQ), material consumption, goods receipt notes (GRN),
warehouse inventory stock shortages, and vendor delivery acceptance rates.
"""

from typing import Dict, Any, List, Optional
import pandas as pd
import numpy as np


class ProcurementEngine:
    """
    Analyzes supply chain execution and material availability.
    Connects procurement bottlenecks to schedule activities using strict relational keys.
    """

    def __init__(
        self,
        boq_df: pd.DataFrame,
        consumption_df: pd.DataFrame,
        receipts_df: pd.DataFrame,
        inventory_df: pd.DataFrame,
        materials_df: pd.DataFrame
    ):
        self.boq_df = boq_df.copy()
        self.consumption_df = consumption_df.copy()
        self.receipts_df = receipts_df.copy()
        self.inventory_df = inventory_df.copy()
        self.materials_df = materials_df.copy()

    def get_kpis(self, project_id: Optional[str] = None) -> Dict[str, Any]:
        """Calculates portfolio or project-level procurement metrics."""
        inv = self.inventory_df
        rec = self.receipts_df
        if project_id:
            inv = inv[inv["project_id"] == project_id] if not inv.empty else inv
            rec = rec[rec["project_id"] == project_id] if not rec.empty else rec

        if inv.empty and rec.empty:
            return {"status": "Insufficient data"}

        # Inventory shortages: closing stock < reserved quantity
        shortages = inv[inv["closing_stock"] < inv["reserved_quantity"]]
        total_shortage_items = len(shortages)
        total_deficit = float((shortages["reserved_quantity"] - shortages["closing_stock"]).sum()) if not shortages.empty else 0.0

        # Receipt quality
        total_receipts = len(rec)
        tot_received = float(rec["received_quantity"].sum()) if total_receipts > 0 else 0.0
        tot_accepted = float(rec["accepted_quantity"].sum()) if total_receipts > 0 else 0.0
        tot_rejected = float(rec["rejected_quantity"].sum()) if total_receipts > 0 else 0.0
        acceptance_pct = round(tot_accepted / tot_received * 100, 2) if tot_received > 0 else 100.0

        rejected_batches = int((rec["rejected_quantity"] > 0).sum())

        return {
            "total_inventory_monitored": len(inv),
            "materials_with_shortage": total_shortage_items,
            "total_stock_deficit_units": round(total_deficit, 2),
            "total_goods_receipts": total_receipts,
            "total_units_received": round(tot_received, 2),
            "total_units_accepted": round(tot_accepted, 2),
            "total_units_rejected": round(tot_rejected, 2),
            "overall_acceptance_rate_pct": acceptance_pct,
            "rejected_shipment_count": rejected_batches
        }

    def get_activity_material_status(self, activity_id: str, project_id: str) -> Dict[str, Any]:
        """
        Gathers evidence regarding materials required for a specific activity,
        actual consumption, current inventory stock, and vendor delivery quality.
        """
        # 1. BOQ Requirement
        if self.boq_df.empty or "project_id" not in self.boq_df.columns or "activity_id" not in self.boq_df.columns:
            return {
                "has_material_requirement": False,
                "materials": [],
                "has_shortage": False,
                "has_delivery_defect": False
            }

        boq_match = self.boq_df[
            (self.boq_df["project_id"] == project_id) &
            (self.boq_df["activity_id"] == activity_id)
        ]

        if boq_match.empty:
            return {
                "has_material_requirement": False,
                "materials": [],
                "has_shortage": False,
                "has_delivery_defect": False
            }

        materials_detail = []
        has_shortage = False
        has_defect = False

        for _, b_row in boq_match.iterrows():
            mat_id = b_row["material_id"]
            planned_qty = float(b_row.get("planned_quantity", 0))
            planned_cost = float(b_row.get("planned_cost", 0))

            # Material master info
            mat_info = {}
            if not self.materials_df.empty:
                m_lookup = self.materials_df[self.materials_df["material_id"] == mat_id]
                if not m_lookup.empty:
                    m = m_lookup.iloc[0]
                    mat_info = {
                        "name": m.get("material_name", mat_id),
                        "category": m.get("category", "N/A"),
                        "criticality": m.get("criticality", "N/A"),
                        "lead_time_days": int(m.get("lead_time_days", 0))
                    }

            # Consumption record
            cons_match = self.consumption_df[
                (self.consumption_df["project_id"] == project_id) &
                (self.consumption_df["activity_id"] == activity_id) &
                (self.consumption_df["material_id"] == mat_id)
            ]
            qty_consumed = float(cons_match["quantity_consumed"].sum()) if not cons_match.empty else 0.0
            remaining_req = float(cons_match["remaining_quantity_required"].sum()) if not cons_match.empty else planned_qty

            # Warehouse stock record for this project & material
            inv_match = self.inventory_df[
                (self.inventory_df["project_id"] == project_id) &
                (self.inventory_df["material_id"] == mat_id)
            ]
            closing_stock = float(inv_match["closing_stock"].iloc[0]) if not inv_match.empty else 0.0
            reserved_stock = float(inv_match["reserved_quantity"].iloc[0]) if not inv_match.empty else 0.0
            is_stock_shortage = closing_stock < reserved_stock
            if is_stock_shortage:
                has_shortage = True

            # Goods receipts & vendor defect history
            grn_match = self.receipts_df[
                (self.receipts_df["project_id"] == project_id) &
                (self.receipts_df["material_id"] == mat_id)
            ]
            vendor_ids = grn_match["vendor_id"].dropna().unique().tolist() if not grn_match.empty else []
            tot_rec = float(grn_match["received_quantity"].sum()) if not grn_match.empty else 0.0
            tot_rej = float(grn_match["rejected_quantity"].sum()) if not grn_match.empty else 0.0
            defect_pct = round(tot_rej / tot_rec * 100, 2) if tot_rec > 0 else 0.0
            if defect_pct > 5.0 or (not grn_match.empty and (grn_match["quality_status"] != "ACCEPTED").any()):
                has_defect = True

            materials_detail.append({
                "material_id": mat_id,
                "material_name": mat_info.get("name", mat_id),
                "category": mat_info.get("category", "N/A"),
                "criticality": mat_info.get("criticality", "N/A"),
                "lead_time_days": mat_info.get("lead_time_days", 0),
                "planned_quantity": planned_qty,
                "planned_cost": planned_cost,
                "quantity_consumed": qty_consumed,
                "remaining_quantity_required": remaining_req,
                "closing_stock": closing_stock,
                "reserved_quantity": reserved_stock,
                "is_stock_shortage": is_stock_shortage,
                "vendors": vendor_ids,
                "defect_pct": defect_pct
            })

        return {
            "has_material_requirement": True,
            "materials": materials_detail,
            "has_shortage": has_shortage,
            "has_delivery_defect": has_defect
        }
