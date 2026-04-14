"""
NVD CVE lookup via NVD REST API v2.
Docs: https://nvd.nist.gov/developers/vulnerabilities

Rate limits (no API key): 5 requests / 30 s
Rate limits (with key):   50 requests / 30 s

Set env var NVD_API_KEY to your key for higher throughput.
"""
import os
import time
import requests
from datetime import datetime

NVD_BASE    = "https://services.nvd.nist.gov/rest/json/cves/2.0"
_API_KEY    = os.environ.get("NVD_API_KEY", "")
_LAST_CALL  = 0.0
_MIN_DELAY  = 6.5   # seconds between calls (safe for no-key tier)


def _throttle():
    global _LAST_CALL
    elapsed = time.time() - _LAST_CALL
    if elapsed < _MIN_DELAY:
        time.sleep(_MIN_DELAY - elapsed)
    _LAST_CALL = time.time()


def _severity_from_score(score: float | None) -> str:
    if score is None:
        return "UNKNOWN"
    if score >= 9.0:
        return "CRITICAL"
    if score >= 7.0:
        return "HIGH"
    if score >= 4.0:
        return "MEDIUM"
    return "LOW"


def _parse_cvss(metrics: dict) -> tuple[float | None, str | None]:
    """Extract the best available CVSS v3.1 → v3.0 → v2 base score."""
    for key in ("cvssMetricV31", "cvssMetricV30"):
        if key in metrics:
            data = metrics[key]
            if data:
                score = data[0]["cvssData"]["baseScore"]
                sev   = data[0]["cvssData"]["baseSeverity"]
                return score, sev
    if "cvssMetricV2" in metrics:
        data = metrics["cvssMetricV2"]
        if data:
            score = data[0]["cvssData"]["baseScore"]
            sev   = _severity_from_score(score)
            return score, sev
    return None, None


def search_cves(keyword: str, max_results: int = 10) -> list[dict]:
    """
    Query NVD for CVEs matching *keyword*.
    Returns a list of normalised CVE dicts.
    """
    _throttle()
    params = {
        "keywordSearch": keyword,
        "resultsPerPage": min(max_results, 20),
        "startIndex": 0,
    }
    headers = {}
    if _API_KEY:
        headers["apiKey"] = _API_KEY

    try:
        resp = requests.get(NVD_BASE, params=params, headers=headers, timeout=15)
        resp.raise_for_status()
        data = resp.json()
    except Exception as exc:
        print(f"[cve_lookup] NVD request failed for '{keyword}': {exc}")
        return []

    results = []
    for item in data.get("vulnerabilities", []):
        cve_obj  = item.get("cve", {})
        cve_id   = cve_obj.get("id", "")
        metrics  = cve_obj.get("metrics", {})
        score, sev = _parse_cvss(metrics)

        # Description (prefer English)
        desc = ""
        for d in cve_obj.get("descriptions", []):
            if d.get("lang") == "en":
                desc = d.get("value", "")
                break

        results.append({
            "cve_id":       cve_id,
            "cvss_score":   score,
            "cvss_severity": sev or _severity_from_score(score),
            "description":  desc,
            "published":    cve_obj.get("published", ""),
            "modified":     cve_obj.get("lastModified", ""),
            "url":          f"https://nvd.nist.gov/vuln/detail/{cve_id}",
        })

    # Sort by CVSS descending
    results.sort(key=lambda x: x["cvss_score"] or 0, reverse=True)
    return results


def lookup_all(search_terms: list[dict]) -> dict[str, list[dict]]:
    """
    Given a list of {component, version, keyword} dicts,
    return {component: [cve_dict, ...]} for each.
    """
    out = {}
    for term in search_terms:
        component = term["component"]
        keyword   = term["keyword"]
        cves      = search_cves(keyword, max_results=10)
        if cves:
            out[component] = {"version": term.get("version", ""), "cves": cves}
    return out
