import math
from typing import Tuple


class GeoService:
    @staticmethod
    def haversine_distance(
        lat1: float,
        lon1: float,
        lat2: float,
        lon2: float
    ) -> float:
        """
        Calculate the great circle distance between two points
        on the earth (specified in decimal degrees)
        Returns distance in meters
        """
        # Convert decimal degrees to radians
        lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
        
        # Haversine formula
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        a = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
        c = 2 * math.asin(math.sqrt(a))
        
        # Radius of earth in meters
        r = 6371000
        
        return c * r

    @staticmethod
    def is_within_geofence(
        student_lat: float,
        student_lon: float,
        class_lat: float,
        class_lon: float,
        radius: int = 100
    ) -> Tuple[bool, float]:
        """
        Check if student is within geofence radius
        Returns (is_within, distance_in_meters)
        """
        distance = GeoService.haversine_distance(
            student_lat, student_lon, class_lat, class_lon
        )
        return distance <= radius, distance
