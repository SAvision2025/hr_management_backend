# services/meetings.py
"""
Pure business-logic helpers.
No Flask, no request/response — only MongoDB operations.
"""

import calendar
from pymongo import MongoClient, errors

# ───────────── Mongo constants ─────────────
URI       = "mongodb+srv://timesheetsystem:SinghAutomation2025@cluster0.alcdn.mongodb.net/"
DB_NAME   = "Timesheet"
ROSTER    = "Employee_meetingdetails"            # static employee master
STATUS    = "Employee_meeting_status"    # month-specific statuses

# ---------------------------------------------------------
# helper: convert “June”, “jun”, “6”  →  1-12 + full name
# ---------------------------------------------------------
def _normalise_month(month_str: str) -> str:
    month_str = month_str.strip()
    if month_str.isdigit():                        # "6"
        n = int(month_str)
        if not 1 <= n <= 12:
            raise ValueError("Month must be 1-12")
        return calendar.month_name[n]              # → "June"
    title = month_str.title()                      # "june" → "June"
    if title in calendar.month_abbr:               # "Jun"
        n = list(calendar.month_abbr).index(title)
        return calendar.month_name[n]              # → "June"
    if title in calendar.month_name:               # "June"
        return title
    raise ValueError("Invalid month value")


# ---------------------------------------------------------
# WRITE / UPDATE one status row
# ---------------------------------------------------------
def save_meeting_status(data: dict) -> tuple[dict, int]:
    """
    Upsert a single (name, manager, month, year) status row.
    Returns: (response_json, http_status)
    """
    required = {"name", "manager", "month", "year", "isCompleted", "notes"}
    if (missing := required.difference(data)):
        return {"error": f"'{missing.pop()}' is required"}, 400

    # normalise & validate month/year
    try:
        month = _normalise_month(data["month"])
        year  = str(data["year"])
    except ValueError as e:
        return {"error": str(e)}, 400

    try:
        col = MongoClient(URI)[DB_NAME][STATUS]
        col.update_one(
            {"name": data["name"],
             "manager": data["manager"],
             "month": month,
             "year": year},
            {"$set": {
                "isCompleted": data["isCompleted"],
                "notes":       data["notes"]
            }},
            upsert=True
        )
        return {"message": "Status saved / updated"}, 200
    except errors.PyMongoError as exc:
        return {"error": str(exc)}, 500


# ---------------------------------------------------------
# READ roster + status for one month
# ---------------------------------------------------------
def fetch_meetings_for_month(manager: str,
                             month: str,
                             year: str) -> list[dict]:
    """
    Returns a list of rows:
      { name, designation, status }
    status = "Completed" | "Pending"
    """
    month = _normalise_month(month)
    year  = str(year)

    client = MongoClient(URI)
    db     = client[DB_NAME]

    # 1️⃣ static employee list for that manager
    roster = list(db[ROSTER].find(
        {"manager": manager},
        {"_id": 0, "name": 1, "designation": 1}
    ))

    # 2️⃣ lookup dict: name → True/False
    status_lookup = {
        d["name"]: d["isCompleted"]
        for d in db[STATUS].find(
            {"manager": manager, "month": month, "year": year},
            {"_id": 0, "name": 1, "isCompleted": 1}
        )
    }

    # 3️⃣ left-join roster ↔ status_lookup
    for emp in roster:
        emp["status"] = "Completed" if status_lookup.get(emp["name"]) else "Pending"

    return roster
