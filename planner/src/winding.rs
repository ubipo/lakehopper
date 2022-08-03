//! Winding of polygons  
//! 'Winding' refers to the order that coordinates of a polygon's rings are
//! stored.

use geo::{winding_order::Winding, MultiPolygon};

/// Ensure `multi_polygon` uses the Open Geospatial Consortium (OGC) Simple
/// Feature Access standard for polygon ring winding order (outer: CCW, inner:
/// CW).
/// ESRI shapefiles notably use the opposite order.
pub fn ensure_sfa_winding(multi_polygon: &mut MultiPolygon<f64>) {
    for polygon in multi_polygon {
        polygon.exterior_mut(|ring| ring.make_ccw_winding());
        polygon.interiors_mut(|rings| {
            for ring in rings {
                ring.make_cw_winding();
            }
        });
    }
}
