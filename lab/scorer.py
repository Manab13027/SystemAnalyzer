"""
Flag submission and scoring logic for the SystemAnalyzer lab.
"""
import hashlib
import db
from lab.challenges import CHALLENGES


def _hash(flag_text: str) -> str:
    return hashlib.sha256(flag_text.encode()).hexdigest()


def submit_flag(username: str, challenge: str, flag_key: str, flag_text: str) -> dict:
    """
    Validate a flag submission.
    Returns dict with keys: correct (bool), message (str), points (int)
    """
    challenge_cfg = CHALLENGES.get(challenge)
    if not challenge_cfg:
        return {"correct": False, "message": "Unknown challenge.", "points": 0}

    flag_cfg = challenge_cfg["flags"].get(flag_key)
    if not flag_cfg:
        return {"correct": False, "message": "Unknown flag.", "points": 0}

    if db.lab_already_solved(username, challenge, flag_key):
        return {
            "correct": True,
            "message": f"Already solved! You earned {flag_cfg['points']} pts for this flag previously.",
            "points": 0,
            "already_solved": True,
        }

    submitted_hash = _hash(flag_text.strip())
    if submitted_hash != flag_cfg["hash"]:
        return {"correct": False, "message": "Incorrect flag. Try again.", "points": 0}

    # Correct — record it
    db.lab_submit_flag(username, challenge, flag_key, flag_cfg["points"])
    return {
        "correct": True,
        "message": f"Correct! +{flag_cfg['points']} points",
        "points": flag_cfg["points"],
        "already_solved": False,
    }


def get_user_progress(username: str) -> dict:
    """
    Returns per-challenge solved flags and total points for a user.
    """
    solves = db.lab_get_user_solves(username)
    solved_map = {}  # challenge -> set of flag_keys
    total_points = 0
    for s in solves:
        solved_map.setdefault(s["challenge"], set()).add(s["flag_key"])
        total_points += s["points"]

    result = {}
    for cname, cfg in CHALLENGES.items():
        total_flags = len(cfg["flags"])
        solved_flags = len(solved_map.get(cname, set()))
        result[cname] = {
            "solved": solved_map.get(cname, set()),
            "total_flags": total_flags,
            "solved_flags": solved_flags,
            "complete": solved_flags == total_flags,
            "challenge_points": sum(
                f["points"] for k, f in cfg["flags"].items()
                if k in solved_map.get(cname, set())
            ),
        }

    return {
        "challenges": result,
        "total_points": total_points,
        "total_flags_solved": sum(len(v) for v in solved_map.values()),
    }
