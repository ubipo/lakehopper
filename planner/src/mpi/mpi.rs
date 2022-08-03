use derive_more::Constructor;

/// A multi polygon coordinate index references a point on one of the rings on a
/// particular polygon by index rather than by coordinate.  
/// This allows for example to retrieve the point's neighbors.
#[derive(Debug, Constructor, Clone, Copy, Default, Eq, PartialEq, PartialOrd, Ord, Hash)]
pub struct Mpi {
    pub polygon_index: usize,
    pub ring_index: usize,
    pub coord_index: usize,
}
