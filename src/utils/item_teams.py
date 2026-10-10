"""
Teams inside one order - from the Quotation page, carried into the Customer Order it
converts into. Each item may carry:

- "team": the team name, and
- "similar_of": the 1-based line number of the row it was added from with "+ Similar"
  (same team and category). Bills list it right under that row.

Items without them (Customer Invoice page, orders saved before this) are one group
with the order's own team_name, so they print as before.
"""
from html import escape
from itertools import groupby

TEAM_MAX_LEN = 100


def clean_team(value) -> str:
    """Trimmed, single-spaced team name (empty when not set)."""
    return " ".join(str(value or "").split())[:TEAM_MAX_LEN]


def apply_item_teams(raw_items: list, normalized: list) -> None:
    """
    Copies "team" and "similar_of" from the page's items onto the normalized items (same
    order). similar_of is kept only when it points to an earlier first row (not itself a
    similar row) of the same team and category; otherwise the item is its own row.
    """
    for raw, item in zip(raw_items, normalized):
        team = clean_team(raw.get("team")) if isinstance(raw, dict) else ""
        if team:
            item["team"] = team
    for index, (raw, item) in enumerate(zip(raw_items, normalized)):
        if not isinstance(raw, dict) or raw.get("similar_of") in (None, ""):
            continue
        try:
            line = int(raw.get("similar_of"))
        except (TypeError, ValueError):
            continue
        if not 1 <= line <= index:
            continue
        first = normalized[line - 1]
        if (first.get("team", "") == item.get("team", "") and first.get("cat_name") == item.get("cat_name")
                and "similar_of" not in first):
            item["similar_of"] = line


def teams_in(items: list) -> list:
    """Team names in the order they first appear."""
    seen = []
    for item in items:
        team = clean_team(item.get("team"))
        if team and team not in seen:
            seen.append(team)
    return seen


def team_names_label(items: list, fallback) -> str:
    """For the order's team_name column: "Team A, Team B", or the page's team_name."""
    teams = teams_in(items)
    return ", ".join(teams) if teams else (fallback or None)


def team_groups(items: list, fallback_team) -> list:
    """
    [(team name, [(line number, item), ...]), ...] in item order - items are saved
    grouped by team. Items without a team form one group named fallback_team.
    """
    numbered = list(enumerate(items, 1))
    return [
        (team or (fallback_team or ""), list(rows))
        for team, rows in groupby(numbered, key=lambda row: clean_team(row[1].get("team")))
    ]


def has_teams(items: list) -> bool:
    return bool(teams_in(items))


def flat_charges_of_team(mockup_charges: list, team: str) -> list:
    """The saved flat charge entries for one team (entries without a team = no-team items)."""
    return [mc for mc in (mockup_charges or []) if clean_team(mc.get("team")) == clean_team(team)]


def flat_charge_label(mc: dict) -> str:
    """'Team A - T-shirt' for a team order's entry, 'T-shirt' otherwise (HTML-escaped)."""
    team = clean_team(mc.get("team"))
    category = escape(str(mc.get("category", "")))
    return f"{escape(team)} - {category}" if team else category
