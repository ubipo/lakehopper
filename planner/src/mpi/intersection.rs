use geo::{Coordinate, MultiPolygon};

use crate::{
    coord_ext::{angle_is_between, AngleTo},
    mpi::{Mpi, NeighborsGetter},
};

pub fn intersects_polygon_locally(
    mpi: &Mpi,    
    ray_to: Coordinate<f64>,
    multi_polygon: &MultiPolygon<f64>,
) -> bool {
    let coord = multi_polygon[mpi];
    let neighbors = mpi.neighbors(multi_polygon);
    let left_angle = coord.angle_to(&multi_polygon[&neighbors.left]);
    let right_angle = coord.angle_to(&multi_polygon[&neighbors.right]);
    let w_p_angle = coord.angle_to(&ray_to);
    return !angle_is_between(w_p_angle, right_angle, left_angle);
}
