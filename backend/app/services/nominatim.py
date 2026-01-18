"""
openstreetmap nominatim geocoding service.
free to use but rate limited to 1 request/second.
"""
import httpx
import time
from typing import Optional

# rate limiting: track last request time
_last_request_time: float = 0.0
_MIN_REQUEST_INTERVAL = 1.1  # slightly over 1 second to be safe


def _rate_limit():
    """ensures we don't exceed nominatim's rate limit"""
    global _last_request_time
    now = time.time()
    elapsed = now - _last_request_time
    if elapsed < _MIN_REQUEST_INTERVAL:
        time.sleep(_MIN_REQUEST_INTERVAL - elapsed)
    _last_request_time = time.time()


def search_places(query: str, limit: int = 5, country_codes: str = "ca,us") -> list[dict]:
    """
    search for places using openstreetmap nominatim.
    returns list of results with name, lat, lon, address.
    biased towards Canada/US by default for better local results.
    """
    _rate_limit()
    
    url = "https://nominatim.openstreetmap.org/search"
    params = {
        "q": query,
        "format": "json",
        "limit": limit,
        "addressdetails": 1,
        "countrycodes": country_codes,  # prioritize Canada and US
        # viewbox around Ontario, Canada for local bias (southwest to northeast)
        "viewbox": "-95.0,41.0,-74.0,56.0",
        "bounded": 0,  # don't strictly bound, just prefer this area
    }
    headers = {
        "User-Agent": "TrickyClip/1.0 (skateboarding clip organizer)"
    }
    
    try:
        response = httpx.get(url, params=params, headers=headers, timeout=10.0)
        response.raise_for_status()
        data = response.json()
        
        results = []
        for item in data:
            results.append({
                "display_name": item.get("display_name", ""),
                "name": item.get("name", item.get("display_name", "").split(",")[0]),
                "latitude": float(item.get("lat", 0)),
                "longitude": float(item.get("lon", 0)),
                "address": _format_address(item.get("address", {})),
                "place_id": item.get("place_id"),
                "osm_type": item.get("osm_type"),
                "osm_id": item.get("osm_id"),
            })
        
        return results
        
    except Exception as e:
        print(f"nominatim search error: {e}")
        return []


def reverse_geocode(lat: float, lon: float) -> Optional[dict]:
    """
    get address from coordinates using nominatim reverse geocoding.
    """
    _rate_limit()
    
    url = "https://nominatim.openstreetmap.org/reverse"
    params = {
        "lat": lat,
        "lon": lon,
        "format": "json",
        "addressdetails": 1,
    }
    headers = {
        "User-Agent": "TrickyClip/1.0 (skateboarding clip organizer)"
    }
    
    try:
        response = httpx.get(url, params=params, headers=headers, timeout=10.0)
        response.raise_for_status()
        data = response.json()
        
        return {
            "display_name": data.get("display_name", ""),
            "name": data.get("name", data.get("display_name", "").split(",")[0]),
            "latitude": float(data.get("lat", lat)),
            "longitude": float(data.get("lon", lon)),
            "address": _format_address(data.get("address", {})),
        }
        
    except Exception as e:
        print(f"nominatim reverse geocode error: {e}")
        return None


def _format_address(addr: dict) -> str:
    """formats nominatim address dict into readable string"""
    parts = []
    
    # street address
    if addr.get("house_number") and addr.get("road"):
        parts.append(f"{addr['house_number']} {addr['road']}")
    elif addr.get("road"):
        parts.append(addr["road"])
    
    # city/town
    city = addr.get("city") or addr.get("town") or addr.get("village") or addr.get("municipality")
    if city:
        parts.append(city)
    
    # state
    if addr.get("state"):
        parts.append(addr["state"])
    
    # country
    if addr.get("country"):
        parts.append(addr["country"])
    
    return ", ".join(parts) if parts else ""

