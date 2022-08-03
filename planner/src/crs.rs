//! Coordinate Reference System (CRS) transformation

use proj::Proj;

/// CRS for internal calculations (like buffering geometries or calculating
/// distances)  
///
/// - 3035:  
///   - name: ETRS89-extended / LAEA Europe
///   - unit: metre  
///   - area of use: Europe  
///
/// https://epsg.io/3035
pub static ETRS_CRS: &str = "EPSG:3035";

/// Good old fashioned web mercator WSG84 for external use (e.g. sending to UI
/// or autopilot)  
///
/// https://epsg.io/4326
pub static WSG_CRS: &str = "EPSG:4326";

/// Projection from internal to external representation.
pub fn create_to_ext_proj() -> Proj {
    // proj::Proj is `!Send`, so we can neither store it in a global static
    // once_cell, nor pass it around in async functions (`!Send` values cannot
    // be used between `.await`'s for spawned tasks).
    // As such, we have to create a fresh instance for each projection job :(
    // It'd probably be a good idea to restrict the area of use
    Proj::new_known_crs(ETRS_CRS, WSG_CRS, None).unwrap()
}

/// Projection from external to internal representation.
pub fn create_to_int_proj() -> Proj {
    // Same comments as `create_to_ext_proj`
    Proj::new_known_crs(WSG_CRS, ETRS_CRS, None).unwrap()
}
