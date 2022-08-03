//! I/O operations for geographic data (geopackage, shapefile...)

use std::error::Error;

use geo::{Geometry, MultiPolygon};
use geozero::wkb;
use sqlx::sqlite::SqlitePoolOptions;

use crate::winding::ensure_sfa_winding;

pub async fn load_gpkg_multi_polygon(
    path: &str,
    name: &str,
) -> Result<MultiPolygon<f64>, Box<dyn Error + Send + Sync>> {
    let uri = format!("sqlite://{}", path);
    let gpkg_pool = SqlitePoolOptions::new()
        .max_connections(5)
        .connect(&uri)
        .await?;

    // `name` is trusted input
    let query = format!("SELECT geom FROM '{}'", name);
    let row: (wkb::Decode<Geometry<f64>>,) = sqlx::query_as(&query).fetch_one(&gpkg_pool).await?;
    let row_geometry = row.0.geometry.expect("gpkg row to have geometry");

    let mut multi_polygon = if let Geometry::MultiPolygon(multi_polygon) = row_geometry {
        multi_polygon
    } else {
        panic!("expected MultiPolygon")
    };
    ensure_sfa_winding(&mut multi_polygon);

    return Ok(multi_polygon);
}

// async fn get_shapefile_obstacles() {
// let grb_geometry_shapes = shapefile::read_shapes("data/iv-grb/small.shp").unwrap();
// assert!(grb_geometry_shapes.len() == 1);
// let mut grb_geometry = if let shapefile::Shape::Polygon(grb_geometry_poly) = &grb_geometry_shapes[0] {
//     MultiPolygon::<f64>::from(grb_geometry_poly.clone())
// } else {
//     panic!("expected Polygon")
// };
// ensure_sfa_winding(&mut grb_geometry);
// }
