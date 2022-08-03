use geo::Coordinate;
use serde::Deserialize;

#[derive(Clone, Debug, Deserialize)]
pub struct LatLng {
    lat: f64,
    lng: f64,
}

impl Into<Coordinate<f64>> for LatLng {
    fn into(self) -> Coordinate<f64> {
        Coordinate {
            x: self.lng,
            y: self.lat,
        }
    }
}
