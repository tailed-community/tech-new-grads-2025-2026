import re
import unicodedata
from typing import Dict, List, Optional

location_cache: Dict[str, dict] = {}

COUNTRY_CODE_TO_NAME = {
    "US": "United States",
    "CA": "Canada",
    "GB": "United Kingdom",
    "IT": "Italy",
    "FR": "France",
    "ES": "Spain",
    "DE": "Germany",
    "IN": "India",
    "NL": "Netherlands",
    "BE": "Belgium",
}

COUNTRY_ALIAS_TO_CODE = {
    "usa": "US",
    "us": "US",
    "united states": "US",
    "united states of america": "US",
    "america": "US",
    "ca": "CA",
    "can": "CA",
    "canada": "CA",
    "uk": "GB",
    "gb": "GB",
    "united kingdom": "GB",
    "italy": "IT",
    "france": "FR",
    "spain": "ES",
    "germany": "DE",
    "india": "IN",
    "netherlands": "NL",
    "belgium": "BE",
}

US_STATES = {
    "AL": "Alabama", "AK": "Alaska", "AZ": "Arizona", "AR": "Arkansas", "CA": "California",
    "CO": "Colorado", "CT": "Connecticut", "DE": "Delaware", "FL": "Florida", "GA": "Georgia",
    "HI": "Hawaii", "ID": "Idaho", "IL": "Illinois", "IN": "Indiana", "IA": "Iowa",
    "KS": "Kansas", "KY": "Kentucky", "LA": "Louisiana", "ME": "Maine", "MD": "Maryland",
    "MA": "Massachusetts", "MI": "Michigan", "MN": "Minnesota", "MS": "Mississippi",
    "MO": "Missouri", "MT": "Montana", "NE": "Nebraska", "NV": "Nevada", "NH": "New Hampshire",
    "NJ": "New Jersey", "NM": "New Mexico", "NY": "New York", "NC": "North Carolina",
    "ND": "North Dakota", "OH": "Ohio", "OK": "Oklahoma", "OR": "Oregon", "PA": "Pennsylvania",
    "RI": "Rhode Island", "SC": "South Carolina", "SD": "South Dakota", "TN": "Tennessee",
    "TX": "Texas", "UT": "Utah", "VT": "Vermont", "VA": "Virginia", "WA": "Washington",
    "WV": "West Virginia", "WI": "Wisconsin", "WY": "Wyoming", "DC": "District of Columbia",
}

CANADA_PROVINCES = {
    "AB": "Alberta", "BC": "British Columbia", "MB": "Manitoba", "NB": "New Brunswick",
    "NL": "Newfoundland and Labrador", "NS": "Nova Scotia", "NT": "Northwest Territories",
    "NU": "Nunavut", "ON": "Ontario", "PE": "Prince Edward Island", "QC": "Quebec",
    "SK": "Saskatchewan", "YT": "Yukon",
}

CITY_ALIASES = {"sf": "San Francisco", "nyc": "New York", "la": "Los Angeles"}
ACCENT_CANON = {"montreal": "Montréal", "quebec": "Québec"}


def normalize_text(text: str) -> str:
    if not text:
        return ""
    normalized = unicodedata.normalize("NFKD", text)
    return normalized.encode("ascii", "ignore").decode("ascii").lower().strip()


def title_case(text: str) -> str:
    return " ".join([part.capitalize() for part in text.split() if part])


def cleanup_raw_location(raw: str) -> str:
    cleaned = re.sub(r"\s+", " ", raw or "").strip()
    cleaned = re.sub(r"\s*,\s*", ", ", cleaned)
    cleaned = re.sub(r"\s+-\s+", " - ", cleaned)
    return cleaned


def strip_decorators(value: str) -> str:
    output = re.sub(r"\bgreater\b", "", value, flags=re.IGNORECASE)
    output = re.sub(r"\bmetro(politan)?\b", "", output, flags=re.IGNORECASE)
    output = re.sub(r"\bmetropolitan city of\b", "", output, flags=re.IGNORECASE)
    output = re.sub(r"\barea\b|\bregion\b", "", output, flags=re.IGNORECASE)
    return re.sub(r"\s+", " ", output).strip()


def classify_location_type(raw: str) -> str:
    key = normalize_text(raw)
    if "remote" in key:
        return "remote"
    if "hybrid" in key:
        return "hybrid"
    return "onsite"


def resolve_country(value: Optional[str]) -> Dict[str, Optional[str]]:
    if not value:
        return {"code": None, "name": None}
    code = COUNTRY_ALIAS_TO_CODE.get(normalize_text(value))
    if not code:
        return {"code": None, "name": None}
    return {"code": code, "name": COUNTRY_CODE_TO_NAME.get(code)}


def resolve_region(value: Optional[str], preferred_country: Optional[str]) -> Dict[str, Optional[str]]:
    if not value:
        return {"code": None, "name": None, "country_code": preferred_country}
    upper = value.strip().upper()
    key = normalize_text(value)
    if preferred_country in (None, "CA"):
        if upper in CANADA_PROVINCES:
            return {"code": upper, "name": CANADA_PROVINCES[upper], "country_code": "CA"}
        for code, name in CANADA_PROVINCES.items():
            if normalize_text(name) == key:
                return {"code": code, "name": name, "country_code": "CA"}
    if preferred_country in (None, "US"):
        if upper in US_STATES:
            return {"code": upper, "name": US_STATES[upper], "country_code": "US"}
        for code, name in US_STATES.items():
            if normalize_text(name) == key:
                return {"code": code, "name": name, "country_code": "US"}
    return {"code": None, "name": title_case(value), "country_code": preferred_country}


def canonical_city(value: Optional[str]) -> Optional[str]:
    if not value:
        return None
    key = normalize_text(value)
    city = CITY_ALIASES.get(key, title_case(value))
    return ACCENT_CANON.get(normalize_text(city), city)


def normalize_location(raw_location: str) -> dict:
    cache_key = raw_location or ""
    if cache_key in location_cache:
        return location_cache[cache_key]
    cleaned = cleanup_raw_location(raw_location)
    stripped = strip_decorators(cleaned)
    loc_type = classify_location_type(cleaned)
    parts = [part.strip() for part in stripped.split(",") if part.strip()]
    city = None
    region = None
    region_code = None
    country = None
    country_code = None
    if len(parts) >= 3:
        city = canonical_city(parts[0])
        region_data = resolve_region(parts[1], None)
        region = region_data["name"]
        region_code = region_data["code"]
        country_data = resolve_country(parts[2])
        country = country_data["name"]
        country_code = country_data["code"] or region_data.get("country_code")
    elif len(parts) == 2:
        city = canonical_city(parts[0])
        country_data = resolve_country(parts[1])
        if country_data["code"]:
            country = country_data["name"]
            country_code = country_data["code"]
        else:
            region_data = resolve_region(parts[1], None)
            region = region_data["name"]
            region_code = region_data["code"]
            country_code = region_data.get("country_code")
            country = COUNTRY_CODE_TO_NAME.get(country_code) if country_code else None
    elif len(parts) == 1:
        token = parts[0]
        country_data = resolve_country(token)
        if country_data["code"]:
            country = country_data["name"]
            country_code = country_data["code"]
        else:
            region_data = resolve_region(token, None)
            if region_data["code"]:
                region = region_data["name"]
                region_code = region_data["code"]
                country_code = region_data.get("country_code")
                country = COUNTRY_CODE_TO_NAME.get(country_code) if country_code else None
            else:
                city = canonical_city(token)
    if loc_type in ("remote", "hybrid"):
        match = re.search(r"\bin\s+([A-Za-z ]+)$", cleaned, flags=re.IGNORECASE)
        if match:
            country_data = resolve_country(match.group(1))
            if country_data["code"]:
                country = country_data["name"]
                country_code = country_data["code"]
    if not country and country_code:
        country = COUNTRY_CODE_TO_NAME.get(country_code)
    unresolved = not any([city, region, country])
    result = {
        "raw": raw_location or "",
        "normalized": {
            "city": city,
            "region": region,
            "region_code": region_code,
            "country": country,
            "country_code": country_code,
        },
        "type": loc_type,
        "unresolved": unresolved,
        "confidence": 0.2 if unresolved else (1.0 if country else 0.7),
    }
    location_cache[cache_key] = result
    return result


def normalize_locations(raw_locations: List[str]) -> List[dict]:
    output: List[dict] = []
    seen = set()
    for raw in raw_locations or []:
        normalized = normalize_location(raw)
        key = "::".join(
            [
                normalized["type"],
                normalized["normalized"].get("country_code") or normalized["normalized"].get("country") or "",
                normalized["normalized"].get("region_code") or normalized["normalized"].get("region") or "",
                normalized["normalized"].get("city") or "",
            ]
        )
        if key not in seen:
            seen.add(key)
            output.append(normalized)
    return output


def validate_location(location: dict) -> bool:
    normalized = location.get("normalized", {})
    country_code = normalized.get("country_code")
    if country_code and country_code not in COUNTRY_CODE_TO_NAME:
        return False
    region_code = normalized.get("region_code")
    if country_code == "US" and region_code and region_code not in US_STATES:
        return False
    if country_code == "CA" and region_code and region_code not in CANADA_PROVINCES:
        return False
    return True
