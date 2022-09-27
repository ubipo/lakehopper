use std::f64::consts::PI;

use geo::MultiPolygon;

use crate::coord_ext::AngleTo;

use super::{Mpi, NeighborsGetter};


pub fn is_locally_concave(mpi: &Mpi, multi_poly: &MultiPolygon<f64>) -> bool {
    let coord = multi_poly[mpi];
    let neighbors = mpi.neighbors(multi_poly);
    let left_angle = coord.angle_to(&multi_poly[&neighbors.left]);
    let right_angle = coord.angle_to(&multi_poly[&neighbors.right]);
    right_angle - left_angle > PI
}

#[cfg(test)]
mod tests {
    #![allow(non_snake_case)]

    use geo::{Coordinate, MultiPolygon, Polygon, LineString};

    use crate::mpi::{Mpi, is_locally_concave};

    #[test]
    fn is_locally_concave__concave() {
        let multi_polygon = MultiPolygon(vec![Polygon::new(
            LineString(vec![
                Coordinate { x: 0.0, y: 0.0 },
                Coordinate { x: 5.0, y: 0.0 },
                Coordinate { x: 2.0, y: 2.0 }, // concave
                Coordinate { x: 0.0, y: 5.0 },
                Coordinate { x: 0.0, y: 0.0 },
            ]),
            vec![],
        )]);
        let mpi = Mpi {
            polygon_index: 0,
            ring_index: 0,
            coord_index: 2,
        };
        assert_eq!(is_locally_concave(&mpi, &multi_polygon), true);
    }

    #[test]
    fn is_locally_concave__convex() {
        let multi_polygon = MultiPolygon(vec![Polygon::new(
            LineString(vec![
                Coordinate { x: 0.0, y: 0.0 },
                Coordinate { x: 5.0, y: 0.0 },
                Coordinate { x: 5.0, y: 5.0 }, // convex
                Coordinate { x: 0.0, y: 5.0 },
                Coordinate { x: 0.0, y: 0.0 },
            ]),
            vec![],
        )]);
        let mpi = Mpi {
            polygon_index: 0,
            ring_index: 0,
            coord_index: 2,
        };
        assert_eq!(is_locally_concave(&mpi, &multi_polygon), false);
    }

    #[test]
    fn is_locally_concave__straight() {
        let multi_polygon = MultiPolygon(vec![Polygon::new(
            LineString(vec![
                Coordinate { x: 0.0, y: 0.0 },
                Coordinate { x: 5.0, y: 0.0 },
                Coordinate { x: 2.5, y: 2.5 }, // straight
                Coordinate { x: 0.0, y: 5.0 },
                Coordinate { x: 0.0, y: 0.0 },
            ]),
            vec![],
        )]);
        let mpi = Mpi {
            polygon_index: 0,
            ring_index: 0,
            coord_index: 2,
        };
        assert_eq!(is_locally_concave(&mpi, &multi_polygon), false);
    }
}
