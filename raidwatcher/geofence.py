from shapely.geometry import Polygon, Point


class Geofence:
    def __init__(self, bounds: list[tuple[float, float]]):
        self.polygon = Polygon(bounds)

    @classmethod
    def from_raw(cls, raw_fence: str):
        bounds = []
        for line in raw_fence.splitlines():
            try:
                lat, lon = line.split(",")
                lat, lon = float(lat), float(lon)
            except ValueError:
                continue

            bounds.append((lat, lon))

        return cls(bounds)

    def contains(self, lat: float, lon: float) -> bool:
        return self.polygon.contains(Point(lat, lon))
