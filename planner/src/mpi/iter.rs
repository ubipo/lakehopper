use std::ops::Index;

use geo::{Coordinate, MultiPolygon};

use super::Mpi;

pub struct MpiIter<'a> {
    parent: &'a MultiPolygon<f64>,
    current: Mpi,
}

impl<'a> Iterator for MpiIter<'a> {
    type Item = Mpi;

    fn next(&mut self) -> Option<Self::Item> {
        if self.current.polygon_index >= self.parent.0.len() {
            return None;
        }
        let polygon = &self.parent.0[self.current.polygon_index];
        if self.current.ring_index >= polygon.interiors().len() + 1 {
            self.current.polygon_index += 1;
            self.current.ring_index = 0;
            self.current.coord_index = 0;
            return self.next();
        }
        let ring = if self.current.ring_index == 0 {
            &polygon.exterior()
        } else {
            &polygon.interiors()[self.current.ring_index - 1]
        };
        // Skip the last coordinate in the ring. A OGC SFA closed ring has the
        // same start and end coordinate. However, we're trying to iterate over
        // all points in the multi-polygon, *not* all the coordinates stored in
        // the data structure.
        let coord_end_index = ring.0.len() - 1;
        if self.current.coord_index >= coord_end_index {
            self.current.ring_index += 1;
            self.current.coord_index = 0;
            return self.next();
        }
        let result = Some(self.current.clone());
        self.current.coord_index += 1;
        return result;
    }
}

pub trait MpiCoordsIterable {
    fn indexed_coords_iter(&self) -> MpiIter;
}

impl MpiCoordsIterable for MultiPolygon<f64> {
    fn indexed_coords_iter(&self) -> MpiIter {
        MpiIter {
            parent: self,
            current: Mpi::default(),
        }
    }
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
