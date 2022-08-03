//! Extensions to `geo::Coordinate`

use std::{
    cmp::Ordering,
    f64::consts::TAU,
    hash::{Hash, Hasher},
};

use geo::{prelude::EuclideanDistance, Coordinate};
use ordered_float::OrderedFloat;

pub trait AngleTo {
    fn angle_to(&self, other: &Self) -> f64;
}

pub trait PseudoangleTo {
    /// Returns a number from the range [-2 .. 2] which is monotonic in the
    /// angle this vector makes against the x axis and with the same
    /// discontinuity as atan2.
    /// Useful for sorting.
    /// Adapted from: https://stackoverflow.com/a/16561333
    /// By Stochastically (https://stackoverflow.com/users/2110762/stochastically)
    fn pseudoangle_to(&self, other: &Self) -> f64;
}

impl AngleTo for Coordinate<f64> {
    fn angle_to(&self, other: &Self) -> f64 {
        let diff = (other.y - self.y).atan2(other.x - self.x);
        if diff < 0.0 {
            diff + TAU
        } else {
            diff
        }
    }
}

impl PseudoangleTo for Coordinate<f64> {
    /// See trait documentation
    fn pseudoangle_to(&self, other: &Self) -> f64 {
        let dx = other.x - self.x;
        let dy = other.y - self.y;
        (1.0-dx/(dx.abs()+dy.abs())).copysign(dy)
    }
}

/// Check whether `angle` is between `low` and `high` (counter clockwise).
///
/// Assumes all angles are in the 0 to TAU range.
pub fn angle_is_between(angle: f64, low: f64, high: f64) -> bool {
    if low < high {
        low <= angle && angle <= high
    } else {
        low <= angle || angle <= high
    }
}

pub fn cmp_angle(
    relative_to: &Coordinate<f64>,
    a: &Coordinate<f64>,
    b: &Coordinate<f64>,
) -> Ordering {
    let pseudoangle_a = relative_to.pseudoangle_to(a);
    let pseudoangle_b = relative_to.pseudoangle_to(b);
    return pseudoangle_a.total_cmp(&pseudoangle_b);
}

pub fn cmp_distance(
    relative_to: &Coordinate<f64>,
    a: &Coordinate<f64>,
    b: &Coordinate<f64>,
) -> Ordering {
    let angle_a = relative_to.euclidean_distance(a);
    let angle_b = relative_to.euclidean_distance(b);
    return angle_a.total_cmp(&angle_b);
}

#[derive(Debug, Clone, Copy, PartialEq)]
pub struct OrderedCoordinate(pub Coordinate<f64>);

impl Hash for OrderedCoordinate {
    fn hash<H: Hasher>(&self, state: &mut H) {
        OrderedFloat(self.0.x).hash(state);
        OrderedFloat(self.0.y).hash(state);
    }
}

impl Eq for OrderedCoordinate {}

#[cfg(test)]
mod tests {
    #![allow(non_snake_case)]
    use std::f64::consts::{FRAC_PI_2, FRAC_PI_4, PI};

    use crate::coord_ext::{angle_is_between, AngleTo};
    use approx::assert_relative_eq;
    use geo::{
        kernels::{Kernel, Orientation, RobustKernel},
        Coordinate,
    };

    #[test]
    fn angle_to___first_quadrant() {
        let a = Coordinate { x: 0.0, y: 0.0 };
        let b = Coordinate { x: 5.0, y: 5.0 };
        assert_relative_eq!(a.angle_to(&b), FRAC_PI_4, epsilon = 0.05);
    }

    #[test]
    fn angle_to___third_quadrant() {
        let a = Coordinate { x: 0.0, y: 0.0 };
        let b = Coordinate { x: -5.0, y: -5.0 };
        assert_relative_eq!(a.angle_to(&b), PI + FRAC_PI_4, epsilon = 0.05);
    }

    #[test]
    fn angle_is_between__normal() {
        assert!(angle_is_between(FRAC_PI_2, 0.0, PI));
    }

    #[test]
    fn angle_is_between__wrap() {
        assert!(angle_is_between(FRAC_PI_2, PI + FRAC_PI_2, PI));
    }

    /// Not a test of our code, just a sanity check of the geo crate.
    #[test]
    fn orient2d__cw() {
        let result = RobustKernel::orient2d(
            Coordinate { x: 0.0, y: 0.0 },
            Coordinate { x: 5.0, y: 0.0 },
            Coordinate { x: 5.0, y: -5.0 },
        );
        assert_eq!(result, Orientation::Clockwise)
    }

    #[test]
    fn orient2d__ccw() {
        let result = RobustKernel::orient2d(
            Coordinate { x: 0.0, y: 0.0 },
            Coordinate { x: 5.0, y: 0.0 },
            Coordinate { x: 5.0, y: 5.0 },
        );
        assert_eq!(result, Orientation::CounterClockwise)
    }
}
