"""
CPM Scheduling Engine
----------------------
Graph-based construction scheduling using NetworkX DAGs.
Implements Critical Path Method (CPM) with:
- Forward pass (Early Start / Early Finish)
- Backward pass (Late Start / Late Finish)
- Float/Slack calculation
- Critical path identification
- Gantt chart data generation

Follows L&T construction sequencing standards.
"""

import json
import uuid
import networkx as nx
from typing import Optional
from app.utils import get_logger

logger = get_logger("scheduler")

# ─── Standard Construction Activity Sequence (L&T Standard) ──────

# Phase → element types mapping with typical durations and dependencies
CONSTRUCTION_PHASES = {
    "P01_SITE_PREPARATION": {
        "name": "Site Preparation & Earthwork",
        "element_types": [],
        "default_duration": 15,
        "predecessors": [],
    },
    "P02_FOUNDATION": {
        "name": "Foundation Work",
        "element_types": ["IfcFooting"],
        "predecessors": ["P01_SITE_PREPARATION"],
    },
    "P03_SUBSTRUCTURE": {
        "name": "Substructure (Basement)",
        "element_types": ["IfcColumn", "IfcBeam", "IfcSlab", "IfcWall"],
        "storeys": ["Foundation", "Basement 1", "Basement 2"],
        "predecessors": ["P02_FOUNDATION"],
    },
    "P04_SUPERSTRUCTURE": {
        "name": "Superstructure",
        "element_types": ["IfcColumn", "IfcBeam", "IfcSlab"],
        "predecessors": ["P03_SUBSTRUCTURE"],
        "per_storey": True,
    },
    "P05_MASONRY": {
        "name": "Masonry & Walls",
        "element_types": ["IfcWall"],
        "predecessors": ["P04_SUPERSTRUCTURE"],
        "per_storey": True,
        "lag": 5,  # Can start 5 days after structure on same floor
    },
    "P06_DOORS_WINDOWS": {
        "name": "Doors & Windows",
        "element_types": ["IfcDoor", "IfcWindow"],
        "predecessors": ["P05_MASONRY"],
        "per_storey": True,
    },
    "P07_ROOFING": {
        "name": "Roofing",
        "element_types": ["IfcRoof"],
        "predecessors": ["P04_SUPERSTRUCTURE"],
    },
    "P08_STAIRS_RAILING": {
        "name": "Stairs & Railings",
        "element_types": ["IfcStair", "IfcRailing"],
        "predecessors": ["P04_SUPERSTRUCTURE"],
    },
    "P09_MEP_ROUGHIN": {
        "name": "MEP Rough-In",
        "element_types": [],
        "default_duration": 20,
        "predecessors": ["P05_MASONRY"],
    },
    "P10_FINISHING": {
        "name": "Finishing & Handover",
        "element_types": [],
        "default_duration": 25,
        "predecessors": ["P06_DOORS_WINDOWS", "P08_STAIRS_RAILING", "P09_MEP_ROUGHIN"],
    },
}


class CPMScheduler:
    """
    Critical Path Method scheduler using NetworkX DAG.

    Creates a construction schedule from BIM elements with predicted
    durations, applies construction sequencing rules, and computes
    the critical path.
    """

    def __init__(self):
        self.graph = nx.DiGraph()
        self.activities: list[dict] = []
        self.critical_path: list[str] = []
        self.total_duration: float = 0

    def build_schedule(
        self,
        elements: list[dict],
        working_hours_per_day: float = 8.0,
        crew_multiplier: float = 1.0,
        custom_dependencies: list[dict] = None,
    ) -> dict:
        """
        Build a complete CPM schedule from BIM elements.

        Args:
            elements: List of BIM element dicts with predicted durations
            working_hours_per_day: Working hours per day
            crew_multiplier: Multiplier for crew size (scenario analysis)
            custom_dependencies: Optional custom dependency rules

        Returns:
            Schedule result dict with gantt data, critical path, etc.
        """
        logger.info(f"Building schedule | elements={len(elements)}")

        # Step 1: Group elements into activities
        activities = self._create_activities(elements, working_hours_per_day, crew_multiplier)

        # Step 2: Build DAG
        self._build_dag(activities, custom_dependencies)

        # Step 3: Validate DAG (check for cycles)
        if not nx.is_directed_acyclic_graph(self.graph):
            raise ValueError("Schedule graph contains cycles. Check dependency rules.")

        # Step 4: Topological sort
        topo_order = list(nx.topological_sort(self.graph))

        # Step 5: Forward pass (ES, EF)
        self._forward_pass(topo_order)

        # Step 6: Backward pass (LS, LF)
        self._backward_pass(topo_order)

        # Step 7: Calculate float and critical path
        self._calculate_float()
        self._find_critical_path()

        # Step 8: Generate output
        result = self._generate_output()

        logger.info(
            f"Schedule complete | total_days={self.total_duration:.1f} | "
            f"critical_activities={len(self.critical_path)}"
        )

        return result

    def _create_activities(
        self, elements: list[dict],
        working_hours_per_day: float,
        crew_multiplier: float
    ) -> list[dict]:
        """Group BIM elements into schedulable activities."""
        # Group elements by (ifc_type, storey)
        groups = {}
        for elem in elements:
            ifc_type = elem.get("ifc_type", "Unknown")
            storey = elem.get("storey", "Unknown")
            key = f"{ifc_type}_{storey}"

            if key not in groups:
                groups[key] = {
                    "elements": [],
                    "ifc_type": ifc_type,
                    "storey": storey,
                    "storey_elevation": elem.get("storey_elevation", 0),
                }
            groups[key]["elements"].append(elem)

        # Convert groups to activities
        activities = []
        for key, group in groups.items():
            total_hours = sum(
                e.get("predicted_duration", e.get("estimated_labor_hours", 8))
                for e in group["elements"]
            )

            crew_size = self._get_crew_size(group["ifc_type"]) * crew_multiplier
            duration_days = max(1, total_hours / (working_hours_per_day * max(1, crew_size)))

            activity = {
                "id": key,
                "name": f"{group['ifc_type'].replace('Ifc', '')} - {group['storey']}",
                "element_type": group["ifc_type"],
                "storey": group["storey"],
                "storey_elevation": group["storey_elevation"],
                "duration": round(duration_days, 1),
                "labor_hours": round(total_hours, 1),
                "crew_size": int(crew_size),
                "element_count": len(group["elements"]),
            }
            activities.append(activity)

        # Add non-element activities (Site Prep, MEP, Finishing)
        for phase_id, phase in CONSTRUCTION_PHASES.items():
            if not phase["element_types"] and "default_duration" in phase:
                activities.append({
                    "id": phase_id,
                    "name": phase["name"],
                    "element_type": None,
                    "storey": "All",
                    "storey_elevation": 0,
                    "duration": phase["default_duration"],
                    "labor_hours": phase["default_duration"] * 8,
                    "crew_size": 10,
                    "element_count": 0,
                })

        # Sort by storey elevation then phase
        activities.sort(key=lambda a: (a["storey_elevation"], a.get("id", "")))
        self.activities = activities
        return activities

    def _build_dag(self, activities: list[dict], custom_deps: list[dict] = None):
        """Build the directed acyclic graph with dependency edges."""
        self.graph = nx.DiGraph()

        # Add all activities as nodes
        for act in activities:
            self.graph.add_node(act["id"], **act)

        # Apply standard construction sequencing rules
        self._apply_construction_rules(activities)

        # Apply custom dependencies
        if custom_deps:
            for dep in custom_deps:
                pred = dep.get("predecessor")
                succ = dep.get("successor")
                lag = dep.get("lag_days", 0)
                if pred in self.graph and succ in self.graph:
                    self.graph.add_edge(pred, succ, lag=lag)

    def _apply_construction_rules(self, activities: list[dict]):
        """Apply L&T standard construction sequencing rules."""
        act_by_id = {a["id"]: a for a in activities}

        # Get unique storeys sorted by elevation
        storeys = sorted(
            set(a["storey"] for a in activities if a["storey"] not in ("All",)),
            key=lambda s: next(
                (a["storey_elevation"] for a in activities if a["storey"] == s), 0
            )
        )

        # Rule 1: Site Prep → Foundation
        if "P01_SITE_PREPARATION" in act_by_id:
            foundation_acts = [a["id"] for a in activities if a.get("element_type") == "IfcFooting"]
            if foundation_acts:
                for fa in foundation_acts:
                    self.graph.add_edge("P01_SITE_PREPARATION", fa, lag=0)
            elif "P02_FOUNDATION" in act_by_id:
                self.graph.add_edge("P01_SITE_PREPARATION", "P02_FOUNDATION", lag=0)

        # Rule 2: Foundation → Ground floor columns
        foundation_acts = [
            a["id"] for a in activities
            if a.get("element_type") == "IfcFooting"
        ]

        # Rule 3: Per-storey sequencing
        for i, storey in enumerate(storeys):
            storey_acts = {
                a["element_type"]: a["id"]
                for a in activities
                if a["storey"] == storey and a["element_type"]
            }

            # Columns/Beams → Slabs (same floor)
            if "IfcColumn" in storey_acts and "IfcSlab" in storey_acts:
                self.graph.add_edge(storey_acts["IfcColumn"], storey_acts["IfcSlab"], lag=0)
            if "IfcBeam" in storey_acts and "IfcSlab" in storey_acts:
                self.graph.add_edge(storey_acts["IfcBeam"], storey_acts["IfcSlab"], lag=0)

            # Columns → Beams (same floor)
            if "IfcColumn" in storey_acts and "IfcBeam" in storey_acts:
                self.graph.add_edge(storey_acts["IfcColumn"], storey_acts["IfcBeam"], lag=0)

            # Slab → Walls (same floor)
            if "IfcSlab" in storey_acts and "IfcWall" in storey_acts:
                self.graph.add_edge(storey_acts["IfcSlab"], storey_acts["IfcWall"], lag=2)

            # Walls → Doors/Windows (same floor)
            if "IfcWall" in storey_acts:
                for elem_type in ("IfcDoor", "IfcWindow"):
                    if elem_type in storey_acts:
                        self.graph.add_edge(storey_acts["IfcWall"], storey_acts[elem_type], lag=0)

            # Foundation → first floor structure
            if i == 0 and foundation_acts:
                for fa in foundation_acts:
                    if "IfcColumn" in storey_acts:
                        self.graph.add_edge(fa, storey_acts["IfcColumn"], lag=0)

            # Previous floor slab → current floor columns (inter-floor dependency)
            if i > 0:
                prev_storey = storeys[i - 1]
                prev_acts = {
                    a["element_type"]: a["id"]
                    for a in activities
                    if a["storey"] == prev_storey and a["element_type"]
                }
                if "IfcSlab" in prev_acts and "IfcColumn" in storey_acts:
                    self.graph.add_edge(prev_acts["IfcSlab"], storey_acts["IfcColumn"], lag=3)

        # Rule 4: Structure → Stairs/Railings
        stair_acts = [a["id"] for a in activities if a.get("element_type") in ("IfcStair", "IfcRailing")]
        slab_acts = [a["id"] for a in activities if a.get("element_type") == "IfcSlab"]
        for sa in stair_acts:
            # Connect to the slab on the same storey
            stair_storey = act_by_id[sa]["storey"]
            matching_slab = next(
                (s for s in slab_acts if act_by_id[s]["storey"] == stair_storey), None
            )
            if matching_slab:
                self.graph.add_edge(matching_slab, sa, lag=0)

        # Rule 5: Structure → Roofing
        roof_acts = [a["id"] for a in activities if a.get("element_type") == "IfcRoof"]
        if roof_acts and slab_acts:
            last_slab = slab_acts[-1]  # Top floor slab
            for ra in roof_acts:
                self.graph.add_edge(last_slab, ra, lag=0)

        # Rule 6: MEP Rough-in after masonry
        wall_acts = [a["id"] for a in activities if a.get("element_type") == "IfcWall"]
        if "P09_MEP_ROUGHIN" in act_by_id and wall_acts:
            # MEP starts after 60% of walls are done (use last wall activity)
            self.graph.add_edge(wall_acts[-1], "P09_MEP_ROUGHIN", lag=0)

        # Rule 7: Finishing after everything
        if "P10_FINISHING" in act_by_id:
            finishing_deps = ["P09_MEP_ROUGHIN"]
            door_acts = [a["id"] for a in activities if a.get("element_type") == "IfcDoor"]
            window_acts = [a["id"] for a in activities if a.get("element_type") == "IfcWindow"]
            if door_acts:
                finishing_deps.append(door_acts[-1])
            if window_acts:
                finishing_deps.append(window_acts[-1])
            if roof_acts:
                finishing_deps.append(roof_acts[-1])
            if stair_acts:
                finishing_deps.append(stair_acts[-1])

            for dep in finishing_deps:
                if dep in self.graph:
                    self.graph.add_edge(dep, "P10_FINISHING", lag=0)

    def _forward_pass(self, topo_order: list[str]):
        """Forward pass: compute Early Start (ES) and Early Finish (EF)."""
        for node_id in topo_order:
            node = self.graph.nodes[node_id]
            duration = node.get("duration", 0)

            # ES = max(EF of all predecessors + lag)
            predecessors = list(self.graph.predecessors(node_id))
            if predecessors:
                es = max(
                    self.graph.nodes[p].get("ef", 0) + self.graph[p][node_id].get("lag", 0)
                    for p in predecessors
                )
            else:
                es = 0

            node["es"] = round(es, 1)
            node["ef"] = round(es + duration, 1)

    def _backward_pass(self, topo_order: list[str]):
        """Backward pass: compute Late Start (LS) and Late Finish (LF)."""
        # Project duration = max EF
        project_duration = max(
            self.graph.nodes[n].get("ef", 0) for n in self.graph.nodes
        )
        self.total_duration = project_duration

        for node_id in reversed(topo_order):
            node = self.graph.nodes[node_id]
            duration = node.get("duration", 0)

            # LF = min(LS of all successors) - lag
            successors = list(self.graph.successors(node_id))
            if successors:
                lf = min(
                    self.graph.nodes[s].get("ls", project_duration) - self.graph[node_id][s].get("lag", 0)
                    for s in successors
                )
            else:
                lf = project_duration

            node["lf"] = round(lf, 1)
            node["ls"] = round(lf - duration, 1)

    def _calculate_float(self):
        """Calculate total float and free float (slack) for each activity."""
        for node_id in self.graph.nodes:
            node = self.graph.nodes[node_id]
            # Total float: time delay without delaying project
            total_float = node.get("ls", 0) - node.get("es", 0)
            node["total_float"] = round(max(0, total_float), 1)
            node["is_critical"] = total_float < 0.1  # Near-zero float = critical
            
            # Free float: time delay without delaying next activities
            successors = list(self.graph.successors(node_id))
            if successors:
                min_succ_es = min(
                    self.graph.nodes[s].get("es", node.get("lf", 0)) - self.graph[node_id][s].get("lag", 0)
                    for s in successors
                )
                free_float = min_succ_es - node.get("ef", 0)
            else:
                free_float = total_float
            node["free_float"] = round(max(0, free_float), 1)

    def _find_critical_path(self):
        """Identify the critical path (activities with zero float)."""
        critical = [
            node_id for node_id in self.graph.nodes
            if self.graph.nodes[node_id].get("is_critical", False)
        ]
        # Sort by early start
        critical.sort(key=lambda n: self.graph.nodes[n].get("es", 0))
        self.critical_path = critical

    def _get_crew_size(self, ifc_type: str) -> int:
        """Get default crew size for an element type."""
        crew_sizes = {
            "IfcFooting": 8, "IfcColumn": 6, "IfcBeam": 6,
            "IfcSlab": 10, "IfcWall": 4, "IfcDoor": 2,
            "IfcWindow": 2, "IfcStair": 6, "IfcRoof": 8,
            "IfcRailing": 3, "IfcCurtainWall": 4,
        }
        return crew_sizes.get(ifc_type, 4)

    def _generate_output(self) -> dict:
        """Generate the final schedule output."""
        gantt_data = []
        for node_id in self.graph.nodes:
            node = self.graph.nodes[node_id]
            predecessors = list(self.graph.predecessors(node_id))

            gantt_item = {
                "id": node_id,
                "name": node.get("name", node_id),
                "element_type": node.get("element_type"),
                "storey": node.get("storey", ""),
                "start_day": node.get("es", 0),
                "end_day": node.get("ef", 0),
                "duration": node.get("duration", 0),
                "early_start": node.get("es", 0),
                "early_finish": node.get("ef", 0),
                "late_start": node.get("ls", 0),
                "late_finish": node.get("lf", 0),
                "total_float": node.get("total_float", 0),
                "free_float": node.get("free_float", 0),
                "is_critical": node.get("is_critical", False),
                "predecessors": predecessors,
                "crew_size": node.get("crew_size", 4),
                "labor_hours": node.get("labor_hours", 0),
                "element_count": node.get("element_count", 0),
            }
            gantt_data.append(gantt_item)

        # Sort by early start
        gantt_data.sort(key=lambda g: g["start_day"])

        # Summary stats
        total_activities = len(gantt_data)
        critical_count = sum(1 for g in gantt_data if g["is_critical"])
        avg_float = (
            sum(g["total_float"] for g in gantt_data) / total_activities
            if total_activities > 0 else 0
        )

        return {
            "project_id": None,  # Set by caller
            "total_duration_days": round(self.total_duration, 1),
            "critical_path": [
                self.graph.nodes[n].get("name", n) for n in self.critical_path
            ],
            "critical_path_duration": round(self.total_duration, 1),
            "gantt_data": gantt_data,
            "summary": {
                "total_activities": total_activities,
                "critical_activities": critical_count,
                "avg_float_days": round(avg_float, 1),
                "max_float_days": round(
                    max((g["total_float"] for g in gantt_data), default=0), 1
                ),
                "total_labor_hours": round(
                    sum(g["labor_hours"] for g in gantt_data), 1
                ),
            },
        }
