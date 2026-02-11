#!/usr/bin/env python3
"""
Quick test to verify project matching works with new normalization.
"""
import re

def canonical_project(value: str) -> str:
    """Normalize project name for fuzzy matching: lowercase, no spaces, no special chars."""
    if not value:
        return ""
    # Remove special characters except letters/numbers, lowercase
    normalized = re.sub(r'[^\w\s]', '', value.lower())
    # Remove all spaces
    normalized = normalized.replace(' ', '')
    return normalized

def match_project_option(project_raw: str, options):
    if not project_raw:
        return None
    candidate = canonical_project(project_raw)
    if not candidate or candidate in {"sinproyecto", "ninguno", "na"}:
        return None
    by_canon = {canonical_project(opt): opt for opt in (options or [])}
    return by_canon.get(candidate)

# Project list
projects = [
    "Comercial Sync",
    "Cooltech",
    "Solkos Intelligence",
    "Cobranza 360°",
    "Coolector iOS",
    "Cask'r app",
    "Coolservice",
    "Vexia",
    "Emerald",
    "Negocon",
    "MIDA",
    "HDI",
    "Other"
]

# Test cases
test_cases = [
    "ComercialSync",
    "comercial sync",
    "COMERCIAL SYNC",
    "Cobranza 360",
    "Cobranza 360°",
    "caskr app",
    "Cask'r app",
    "HDI",
    "hdi",
    "Emerald",
    "EMERALD",
    "vexia"
]

print("Testing Project Matching:")
print("="*50)
for test in test_cases:
    matched = match_project_option(test, projects)
    status = "✅" if matched else "❌"
    print(f"{status} \"{test}\" -> {matched}")
