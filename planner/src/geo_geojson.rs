//! `geo` to `geojson` conversions

use geo::{Geometry, MultiPolygon, Point, MultiPoint};
use geojson::Feature;
use proj::Transform;

use crate::crs::create_to_ext_proj;

pub fn geometry_to_feature(mut geometry: Geometry<f64>) -> geojson::Feature {
    let proj = create_to_ext_proj();
    geometry.transform(&proj).unwrap();
    return Feature::from(geojson::Geometry::from(&geometry));
}

pub fn multi_polygon_to_feature(mut multi_polygon: MultiPolygon<f64>) -> geojson::Feature {
    let proj = create_to_ext_proj();
    multi_polygon.transform(&proj).unwrap();
    return Feature::from(geojson::Geometry::from(&multi_polygon));
}

pub fn feature_from_points(points: impl Iterator<Item = Point<f64>>) -> geojson::Feature {
    let proj = create_to_ext_proj();
    let multi_point = MultiPoint(points.map(|point| {
        point.transformed(&proj).unwrap()
    }).collect::<Vec<_>>());
    return Feature::from(geojson::Geometry::from(&multi_point));
}
