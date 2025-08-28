"""
Analytics module for Slink Platform.

Responsibilities:
    - Track clicks on slinks
    - Track source of click (browser or API)
    - Track validity of slink clicks
    - Provide summary statistics

Attributes:
    click_logs (Dict[str, List[Dict]]): Maps slink_code -> list of click events

LLM Prompt Example:
    "Explain how to extend this analytics module to store click events
    in a persistent database while preserving existing API."
"""

import time
from typing import Dict, List


class Analytics:
    def __init__(self):
        """
        Initialize empty click log dictionary.

        _clicks structure:
        { slink_code: [ {"timestamp": float, "source": str, "valid": bool}, ... ] }
        """
        self.click_logs: Dict[str, List[Dict]] = {}

    def log_click(self, slink_code: str, source: str = "browser", valid: bool = True) -> None:
        """
        Log a click event for a slink.

        Args:
            slink_code (str): The shortened URL code clicked.
            source (str): Source of click ('browser' or 'api').
            valid (bool): Whether the slink is valid (exists in storage).

        Notes:
            - If slink_code does not exist, initializes log list.
            - This design allows future persistent storage integration.

        LLM Prompt Example:
            "Show how to extend this method to batch logs to a cloud database asynchronously."
        """
        if slink_code not in self.click_logs:
            self.click_logs[slink_code] = []
        self.click_logs[slink_code].append({
            "timestamp": time.time(),
            "source": source,
            "valid": valid
        })

    def get_clicks(self, slink_code: str, only_valid: bool = False) -> List[Dict]:
        """
        Get all click events for a given slink_code.

        Args:
            slink_code (str): Short code to query.
            only_valid (bool): If True, return only clicks where valid=True.

        Returns:
            List[Dict]: List of click events, empty if none exist.
        """
        logs = self.click_logs.get(slink_code, [])
        if only_valid:
            logs = [log for log in logs if log.get("valid", True)]
        return logs

    def summary(self, only_valid: bool = False) -> Dict[str, Dict]:
        """
        Get a summary of click events for all slinks.

        Args:
            only_valid (bool): If True, include only valid clicks in summary.

        Returns:
            Dict[str, Dict]: Dictionary mapping slink_code -> summary including:
                - total_clicks: int
                - last_click: float timestamp or None
                - sources: dict with source counts
                - valid_clicks: int (total valid clicks)

        Example:
            {
                "iAxdGL": {
                    "total_clicks": 5,
                    "last_click": 1755835287.5517154,
                    "sources": {"browser": 3, "api": 2},
                    "valid_clicks": 4
                }
            }

        Notes:
            - The `if filtered_logs else None` branch for `last_click` is primarily
              defensive. Under normal operation `click_logs` entries are never empty,
              but this protects against unexpected states or future refactors.
              Tests may inject an empty list explicitly to validate this branch.

        LLM Prompt Example:
            "Suggest ways to extend this summary to include daily/weekly aggregation."
        """
        summary_data: Dict[str, Dict] = {}
        for slink_code, logs in self.click_logs.items():
            filtered_logs = [log for log in logs if log.get("valid", True)] if only_valid else logs

            # Skip entries if only_valid=True and no valid clicks
            if only_valid and not filtered_logs:
                continue

            sources_count: Dict[str, int] = {}
            for log in filtered_logs:
                src = log["source"]
                sources_count[src] = sources_count.get(src, 0) + 1

            summary_data[slink_code] = {
                "total_clicks": len(filtered_logs),
                # Defensive: filtered_logs is normally non-empty here,
                # but we safeguard against unexpected empty lists.
                "last_click": filtered_logs[-1]["timestamp"] if filtered_logs else None,
                "sources": sources_count,
                "valid_clicks": sum(1 for log in logs if log.get("valid", True))
            }
        return summary_data
