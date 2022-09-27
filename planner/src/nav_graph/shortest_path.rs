use geo::{Coordinate, prelude::EuclideanDistance};
use petgraph::{algo::astar, stable_graph::NodeIndex};

use crate::crs::create_to_int_proj;

use super::{NavGraph, Edge, add_coord_to_nav_graph, VisibilityOptimizationMode};

pub fn calculate_shortest_path_between_coords(
    nav_graph: &mut NavGraph,
    start_coord: Coordinate<f64>,
    end_coord: Coordinate<f64>,
    visibility_optimization_mode: VisibilityOptimizationMode,
) -> Option<(Edge, Vec<NodeIndex>)> {
    // Projection needs to be in a separate scope because `proj::Proj`
    // is `!Send`.
    let (start_coord, end_coord) = {
        let proj = create_to_int_proj();
        (
            proj.project(start_coord, false).unwrap(),
            proj.project(end_coord, false).unwrap(),
        )
    };
    let (_, start_index) = add_coord_to_nav_graph(start_coord, nav_graph, None, visibility_optimization_mode);
    let (_, end_index) = add_coord_to_nav_graph(end_coord, nav_graph, None, visibility_optimization_mode);
    
    return calculate_shortest_path(nav_graph, start_index, end_index);
}

pub fn calculate_shortest_path(
    nav_graph: &NavGraph, start_index: NodeIndex, end_index: NodeIndex
) -> Option<(Edge, Vec<NodeIndex>)> {
    let end_coord = nav_graph.features.coord(nav_graph.graph.node_weight(end_index).unwrap());
    astar(
        &nav_graph.graph.clone(),
        start_index,
        |n| n == end_index,
        |e| *e.weight(),
        |node_index| {
            let node_data = nav_graph.graph.node_weight(node_index).unwrap();
            let coord = nav_graph.features.coord(node_data);
            Edge::new(coord.euclidean_distance(&end_coord))
        },
    )
}