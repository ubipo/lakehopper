//! Algorithms to compute the visibility of points in the plane& for the purpose
//! of creating visibility/navigation graph.
//! 
//! Adapted from:
//! de Berg, M. et al. (2008) Computational Geometry: Algorithms and Applications. 
//! Berlin, Heidelberg: Springer Berlin Heidelberg.
//! https://doi.org/10.1007/978-3-540-77974-2.

use derive_more::Constructor;
use geo::{
    kernels::Kernel,
    kernels::{Orientation, RobustKernel},
    line_intersection::{line_intersection, LineIntersection},
    lines_iter::LinesIter,
    prelude::{Contains, EuclideanDistance},
    Coordinate, Line, MultiPolygon, Point, GeometryCollection
};
use serde::Deserialize;
use take_until::TakeUntilExt;

use crate::{
    coord_ext::{cmp_angle, cmp_distance},
    intersection::get_proper_ray_line_intersection,
    mpi::{Mpi, NeighborsGetter},
    multi_polygon_intersection::intersects_polygon_locally, dgc::DebugGeometryCallback,
};

use super::graph_types::{NodeData, Features};

/// Maximum distance between two points for them to be considered the same point
/// and thus trivially visible to each other. Expressed in the unit of the
/// features geometry's CRS.
static SAME_POINT_VISIBILITY_DISTANCE: f64 = 0.5;

#[derive(PartialEq, Clone, Copy, Debug, Deserialize)]
pub enum VisibilityOptimizationMode {
    Naive, // No optimizations
    Sweep, // Sweep optimization (de Berg et al. 2008)
    OptimizedSweep, // Sweep with inner-outer ring culling and `in front` angle range optimizations
}

#[derive(Constructor)]
struct WPrevInfo <'a> {
    w_prev: &'a NodeData,
    w_prev_visible: bool,
}

fn is_visible_from(
    p: &NodeData,
    w_prev_info: Option<&WPrevInfo>,
    w: &NodeData,
    possible_obstacle_edges: &Vec<Line<f64>>,
    features: &Features,
    optimization_mode: VisibilityOptimizationMode,
    _dgc: DebugGeometryCallback,
) -> bool {
    let p_coord = features.coord(&p);
    let w_coord = features.coord(w);

    if optimization_mode != VisibilityOptimizationMode::OptimizedSweep && let NodeData::PartOfObstacle(p_mpi) = p {
        if intersects_polygon_locally(p_mpi, w_coord, &features.obstacles) {
            return false;
        }
    }

    if let NodeData::PartOfObstacle(w_mpi) = w {
        // 1. if p-w intersects the interior of the obstacle of which w is a
        // vertex, locally at w
        if intersects_polygon_locally(w_mpi, p_coord, &features.obstacles) {
            // 2. then return false
            return false;
        }
    }
    
    let p_w = Line::new(p_coord, w_coord);

    if optimization_mode == VisibilityOptimizationMode::Naive {
        let p_w_intersects_any_edge = possible_obstacle_edges.iter()
            .filter(|obstacle_edge| {
                !(obstacle_edge.start == w_coord || obstacle_edge.end == w_coord)
            })
            .any(|obstacle_edge| {
                line_intersection(*obstacle_edge, p_w).is_some_and(|int| int.is_proper())
            });
        return !p_w_intersects_any_edge
    }

    // 3. if i = 1 or w_prev is not on the segment p-w

    // if else inverted from de Berg et al.'s notation
    if 
        let Some(WPrevInfo { w_prev, w_prev_visible }) = w_prev_info
        && p_w.contains(&features.coord(w_prev))
    {
        // 8. if w_prev is not visible
        if !w_prev_visible { false }
        else {
            // 10. Search in T for an edge e that intersects w_prev-w.
            // 11. if e exists
            // 12.   then return false
            // 13.   else return true
            let w_prev_coord = features.coord(w_prev);
            let w_prev_w = Line::new(w_prev_coord, w_coord);
            let e_exists = possible_obstacle_edges.iter().any(|obstacle_edge| {
                line_intersection(*obstacle_edge, w_prev_w).is_some()
            });
            !e_exists
        }
    } else {
        // 4. Search in T for the edge e in the leftmost leaf.
        // 5.   if e exists and p-w intersects e
        // 6.     then return false
        // 7.     else return true

        // As discussed when creating T, there is no point in using a sorted
        // data structure, as such we just iterate over all the edges in search
        // for an intersection.
        let p_w_intersects_any_edge = possible_obstacle_edges.iter()
            .filter(|obstacle_edge| {
                !(obstacle_edge.start == w_coord || obstacle_edge.end == w_coord)
            })
            .any(|obstacle_edge| {
                line_intersection(*obstacle_edge, p_w).is_some()
            });
        return !p_w_intersects_any_edge;
    }
}

// Implements steps 6 and 7 of the VisibleVertices() algorithm by de Berg et
// al..
//
// 6. Insert into T the obstacle edges incident to w that lie on the
// [ccw] side of the half-line from p to w.
// ...and...
// 7. Delete from T the obstacle edges incident to w that lie on the
// ~counterclockwise~(*clockwise) side of the half-line from p to w.
fn update_possible_obstacle_edges(
    p_coord: Coordinate<f64>,
    w_mpi: &Mpi,
    obstacles: &MultiPolygon<f64>,
    possible_obstacle_edges: &mut Vec<Line<f64>>
) {
    let w_coord = obstacles[w_mpi];
    let w_neighbors = w_mpi.neighbors(obstacles);
    let w_left_coord = obstacles[&w_neighbors.left];
    let w_right_coord = obstacles[&w_neighbors.right];

    // The order of `Line::start` and `Line::end` needs to be the same as Lines
    // returned by MultiPolygon::lines_iter(). Otherwise BTreeSet::contains
    // would fail. The line is oriented right to left.
    let left_incident_edge = Line::new(w_coord, w_left_coord);
    // Same here; right to left.
    let right_incident_edge = Line::new(w_right_coord, w_coord);

    [
        (left_incident_edge, w_left_coord),
        (right_incident_edge, w_right_coord),
    ]
    .map(|(neighbor_edge, neighbor_coord)| {
        let orientation = RobustKernel::orient2d(p_coord, w_coord, neighbor_coord);
        let existing_index = possible_obstacle_edges
            .iter()
            .enumerate()
            .find(|(_, edge)| neighbor_edge == **edge)
            .map(|(i, _)| i);
        if orientation == Orientation::CounterClockwise {
            if existing_index.is_none() {
                possible_obstacle_edges.push(neighbor_edge);
            }
        } else {
            if existing_index.is_some() {
                possible_obstacle_edges.swap_remove(existing_index.unwrap());
            }
        }
    });
}

/// `p` is the point (/vertex) in question  
/// `ws` is the collection of other points to check visibility to
///
///  From "Computational Geometry: Algorithms and Applications" (de Berg et al.,
/// 2008)
pub fn visible_vertices<'a>(
    p: &NodeData,
    ws: &'a mut Vec<NodeData>,
    features: &Features,
    _dgc: DebugGeometryCallback,
    optimization_mode: VisibilityOptimizationMode,
) -> Vec<NodeData> {
    let p_coord = features.coord(&p);

    // 1. Sort the obstacle vertices according to the [ccw] angle that the
    //    halfline from p to each vertex makes with the positive x-axis. In case
    //    of ties, vertices closer to p should come before vertices farther from
    //    p.

    match optimization_mode {
        VisibilityOptimizationMode::Naive => { }
        VisibilityOptimizationMode::Sweep |
        VisibilityOptimizationMode::OptimizedSweep => {
            // Sort in-place. This speeds up sorting since it's likely that a
            // neighboring vertex (that we'll process later if p is part of an obstacle)
            // has similar angle/distance order.
            ws.sort_by(|a, b| {
                cmp_angle(&p_coord, &features.coord(a), &features.coord(b))
                    .then_with(|| cmp_distance(&p_coord, &features.coord(a), &features.coord(b)))
            });
        }
    }


    let ws_iter = ws.iter().copied()
        // p is trivially visible from p itself; do not consider this case
        .filter(|w| w != p);
    let ws_applicable = match p {
        NodeData::PartOfObstacle(p_mpi) => match optimization_mode {
            VisibilityOptimizationMode::Naive |
            VisibilityOptimizationMode::Sweep => ws_iter.collect::<Vec<_>>(),
            VisibilityOptimizationMode::OptimizedSweep => {
                // Only consider vertices "in front" of p, with "in front"
                // meaning within the range of angles between p's two neighbors.
                // Vertices "behind" this p would always intersect the polygon p
                // is part of. "take_until" (not part of stdlib) is like
                // "take_while", except inclusive see:
                // https://github.com/rust-lang/rust/issues/62208
                let p_neighbor_mpis = p_mpi.neighbors(&features.obstacles);
                ws_iter.cycle()
                    .skip_while(|w| *w != NodeData::PartOfObstacle(p_neighbor_mpis.right))
                    .take_until(|w| *w == NodeData::PartOfObstacle(p_neighbor_mpis.left))
                    .filter(|w| {
                        // If w is part of the same polygon that p is a part of,
                        // then w can be visible iff it is on the same ring. This is
                        // true both for the outer ring and inner rings.
                        if
                            let NodeData::PartOfObstacle(w_mpi) = w
                            && w_mpi.polygon_index == p_mpi.polygon_index
                        {
                            w_mpi.ring_index == p_mpi.ring_index
                        } else { true }
                    })
                    .collect::<Vec<_>>()
            },
        }
        // Water is not an obstacle (visibility lines can cross water),
        // so we can just return the entire list.
        NodeData::PartOfWater(_) |
        // We cannot consider only vertices "in front" of p, since p is not
        // part of an obstacle.
        NodeData::Arbitrary(_) => {
            ws_iter.collect::<Vec<_>>()
        }
    };

    // Mark any point within a margin as visible regardless of obstacle
    // intersections. This also avoids problems with for example water
    // points overlapping with obstacle point and leading to undefined
    // angles.
    let mut ws_same_location = Vec::new();
    let ws_applicable = ws_applicable.iter()
        .filter(|w| {
            let distance = features.coord(w).euclidean_distance(&p_coord);
            let is_same_location = distance <= SAME_POINT_VISIBILITY_DISTANCE;
            if is_same_location {
                ws_same_location.push(*w);
            }
            !is_same_location
        })
        .copied()
        .collect::<Vec<_>>();

    // _dgc.clone().unwrap().try_send(geo::Geometry::GeometryCollection(GeometryCollection::from_iter(ws_applicable.iter().map(|w| {
    //     Point(features.coord(w))
    // })))).unwrap();
    // _dgc.clone().unwrap().try_send(geo::Geometry::Point(geo::Point(p_coord))).unwrap();

    let mut possible_obstacle_edges = match optimization_mode {
        VisibilityOptimizationMode::Naive => {
            features.obstacles.lines_iter().collect::<Vec<Line<f64>>>()
        }
        VisibilityOptimizationMode::Sweep |
        VisibilityOptimizationMode::OptimizedSweep => {
            // 2. Let rho be the half-line parallel to the positive x-axis starting at p.
            //    Find the obstacle edges that are properly intersected by rho, and store
            //    them in a balanced search tree T in the order in which they are
            //    intersected by rho.

            if ws_applicable.is_empty() { return Default::default(); }

            // Because we only consider vertices in front of p, let rho be the half-line
            // parallel to the first of those vertices (instead of parallel to the
            // x-axis).
            let most_clockwise_w_coord = features.coord(&ws_applicable[0]);
            let rho = Line::new(p_coord, most_clockwise_w_coord);

            // The first edge needs to always be the first possible obstacle for every w
            // later considered. But because edges can be oriented in any way, the
            // ordering can change depending on which w is considered, so we need to
            // sort the edges for each w.
            // Sorting the edges for each w requires calculating the intersection of rho
            // oriented along p-w with every edge in the tree. This sort actually has a
            // worse worst-case time complexity of O(n*log(n)) as compared to just
            // iterating over the edges (O(n)) (the best-case time complexities are
            // identical). As such, there is no point in sorting the edges in the first
            // place.
            // It is however useful to keep the edges in a hash set. This speeds up the
            // lookup required for steps 6 and 7 of this method (`visible_vertices()`).
            features.obstacles
                .lines_iter()
                .filter(|edge| get_proper_ray_line_intersection(rho, edge).is_some())
                .collect::<Vec<Line<f64>>>()
        }
    };

    // holds w_prev as well as wether w_prev was visible (w_prev is called w
    // i-1 in de Berg et al., 2008
    let mut w_prev_info: Option<WPrevInfo> = None;

    // 4. for [w in ws_applicable]
    let mut ws_visible = ws_applicable.iter().filter(|w| {
        // 5. if VISIBLE(wi) then Add w to W
        let is_visible =
            is_visible_from(p, w_prev_info.as_ref(), w, &possible_obstacle_edges, features, optimization_mode, _dgc.clone());
        w_prev_info = Some(WPrevInfo::new(&w, is_visible));

        // 6. and 7.
        if optimization_mode != VisibilityOptimizationMode::Naive && let NodeData::PartOfObstacle(w_mpi) = w {
            update_possible_obstacle_edges(p_coord, w_mpi, &features.obstacles, &mut possible_obstacle_edges);
        }
        
        return is_visible;
    })
    .copied()
    .collect::<Vec<_>>();

    ws_visible.extend(ws_same_location);

    return ws_visible;
}
