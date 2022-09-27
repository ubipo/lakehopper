use std::ops::Index;
use derive_more::Constructor;
use geo::{MultiPolygon, Coordinate};


/// A multi polygon coordinate index references a point on one of the rings on a
/// particular polygon by index rather than by coordinate.  
/// This allows for example to retrieve the point's neighbors.
#[derive(Debug, Constructor, Clone, Copy, Default, Eq, PartialEq, PartialOrd, Ord, Hash)]
pub struct Mpi {
    pub polygon_index: usize,
    pub ring_index: usize,
    pub coord_index: usize,
}


impl<'a> Index<&Mpi> for &'a MultiPolygon<f64> {
    type Output = Coordinate<f64>;

    fn index(&self, index: &Mpi) -> &Self::Output {
        let polygon = &self.0[index.polygon_index];
        let ring = if index.ring_index == 0 {
            &polygon.exterior()
        } else {
            &polygon.interiors()[index.ring_index - 1]
        };
        let res = &ring.0[index.coord_index];
        res
    }
}
