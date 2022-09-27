use derive_more::Constructor;
use geo::MultiPolygon;

use crate::modulo::ModuloSignedExt;

use super::Mpi;

/// Left and right neighbors of a multi-polygon index, as if looking out from
/// within. Left neighbor has ring index +1, right neighbor has ring index -1.
#[derive(Debug, Constructor)]
pub struct Neighbors {
    pub left: Mpi,
    pub right: Mpi,
}

impl Into<[Mpi; 2]> for Neighbors {
    fn into(self) -> [Mpi; 2] {
        [self.left, self.right]
    }
}

pub trait NeighborsGetter {
    /// Return the neighbors of this multi-polygon index.
    fn neighbors(&self, multi_poly: &MultiPolygon<f64>) -> Neighbors
    where
        Self: Sized;
}

impl NeighborsGetter for Mpi {
    fn neighbors(&self, multi_poly: &MultiPolygon<f64>) -> Neighbors
    where
        Self: Sized,
    {
        let polygon = &multi_poly.0[self.polygon_index];
        let ring = if self.ring_index == 0 {
            &polygon.exterior()
        } else {
            &polygon.interiors()[self.ring_index - 1]
        };

        // Ignore the last coordinate of the ring (- 1), as it is the same as
        // the first one.
        let nbro_coords = ring.0.len() as i64 - 1;

        let coord_index = self.coord_index as i64;

        // OGC SFA Outer rings are CCW, inner are CW
        // https://www.ogc.org/standards/sfa
        // As such, the left neighbor has a larger index, the right one a
        // smaller, both for outer and inner rings.
        let mut left_neighbor = self.clone();
        left_neighbor.coord_index = (coord_index + 1).modulo(nbro_coords) as usize;
        let mut right_neighbor = self.clone();
        right_neighbor.coord_index = (coord_index - 1).modulo(nbro_coords) as usize;

        return Neighbors::new(left_neighbor, right_neighbor);
    }
}
