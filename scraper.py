import requests
from bs4 import BeautifulSoup
from collections import Counter
from config import ORANGE_EMAIL, ORANGE_PASSWORD, ORANGE_LOGIN_URL, ORANGE_CLI_URL
import logging

logger = logging.getLogger(__name__)

SESSION = None

def get_session():
    global SESSION
    if SESSION is None:
        SESSION = login()
    return SESSION

def login():
    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    })
    try:
        # Get login page for CSRF token
        resp = session.get(ORANGE_LOGIN_URL, timeout=15)
        soup = BeautifulSoup(resp.text, "html.parser")
        
        # Try to find CSRF token
        csrf = None
        csrf_input = soup.find("input", {"name": "_token"})
        if csrf_input:
            csrf = csrf_input.get("value")

        payload = {
            "email": ORANGE_EMAIL,
            "password": ORANGE_PASSWORD,
        }
        if csrf:
            payload["_token"] = csrf

        login_resp = session.post(ORANGE_LOGIN_URL, data=payload, timeout=15, allow_redirects=True)
        
        if "dashboard" in login_resp.url or "logout" in login_resp.text.lower():
            logger.info("Orange Carrier login successful")
            return session
        else:
            logger.error(f"Login failed. URL: {login_resp.url}")
            return None
    except Exception as e:
        logger.error(f"Login error: {e}")
        return None

def search_cli(prefix, session):
    try:
        resp = session.get(
            ORANGE_CLI_URL,
            params={"search": prefix},
            timeout=20
        )
        soup = BeautifulSoup(resp.text, "html.parser")
        
        # Find table rows
        rows = soup.find_all("tr")
        terminations = []
        
        for row in rows:
            cells = row.find_all("td")
            if cells and len(cells) >= 2:
                termination = cells[0].get_text(strip=True)
                if termination and termination != "Termination":
                    terminations.append(termination)
        
        return terminations
    except Exception as e:
        logger.error(f"Search error for {prefix}: {e}")
        return []

def analyze_results(terminations, min_hits=4, max_hits=10):
    """Count how many times each termination range appears"""
    counter = Counter(terminations)
    filtered = {k: v for k, v in counter.items() if min_hits <= v <= max_hits}
    return filtered

def scrape_active_ranges(cli_list, min_hits=4, max_hits=10, top_n=20, window_minutes=30):
    global SESSION
    session = get_session()
    if not session:
        SESSION = login()
        session = SESSION
    if not session:
        return None, "Login failed"

    all_results = {}  # termination -> {hits, clis, last_cli}

    for prefix in cli_list:
        terminations = search_cli(prefix, session)
        if terminations is None:
            # Try re-login once
            SESSION = login()
            session = SESSION
            if session:
                terminations = search_cli(prefix, session)
            else:
                continue

        for term in terminations:
            if term not in all_results:
                all_results[term] = {"hits": 0, "clis": set(), "last_cli": prefix}
            all_results[term]["hits"] += 1
            all_results[term]["clis"].add(prefix)
            all_results[term]["last_cli"] = prefix

    # Filter by hit count
    filtered = {
        k: v for k, v in all_results.items()
        if min_hits <= v["hits"] <= max_hits
    }

    # Sort by hits descending
    sorted_results = sorted(filtered.items(), key=lambda x: x[1]["hits"], reverse=True)[:top_n]

    return sorted_results, None
