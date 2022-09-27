use std::{collections::HashMap, time::Duration};

use geo::{
    prelude::{Contains, EuclideanDistance},
    Coordinate, Point,
};
use petgraph::{graph::NodeIndex, Graph};

use crate::{coord_ext::OrderedCoordinate, dgc::DebugGeometryCallback, mpi::is_locally_concave};

use super::{
    graph_types::{Edge, Features, NodeData},
    visibility::{visible_vertices, VisibilityOptimizationMode},
    NavGraph,
};



fn add_visible_edges(
    p: &NodeData,
    ws: &mut Vec<NodeData>,
    nav_graph: &mut NavGraph,
    dgc: DebugGeometryCallback,
    optimization_mode: VisibilityOptimizationMode,
) {
    let p_coord = nav_graph.features.coord(&p);
    let ws_visible = visible_vertices(p, ws, &nav_graph.features, dgc.clone(), optimization_mode);
    for w_visible in ws_visible {
        let w_visible_coord = nav_graph.features.coord(&w_visible);
        let weight = p_coord.euclidean_distance(&w_visible_coord);
        let edge = Edge::new(weight);
        nav_graph.graph.update_edge(
            nav_graph.node_data_index_map[&p],
            nav_graph.node_data_index_map[&w_visible],
            edge,
        );
    }
}


pub fn create_nav_graph<'a>(
    features: &Features,
    dgc: DebugGeometryCallback,
    optimization_mode: VisibilityOptimizationMode,
) -> (NavGraph, Duration) {
    println!(
        "Creating nav graph with optimization mode: {:?}",
        optimization_mode
    );

    let mut graph = Graph::new_undirected();
    let mut vertices = features
        .iter()
        .filter(|node_data| {
            // Do not consider water nodes for the graph
            if let NodeData::PartOfWater(_) = node_data {
                return false;
            }

            // Do not consider points within obstacles for the graph
            let lies_within_obstacle = features
                .obstacles
                .contains(&Point(features.coord(node_data)));
            if lies_within_obstacle { return false; }

            // return if optimization_mode == VisibilityOptimizationMode::OptimizedSweep {
            //     // Points that are locally concave (pointing inward) would never
            //     // be part of the optimal path (why enter a hole if you can just
            //     // skip it) => do not consider.
            //     let is_locally_concave = match node_data {
            //         NodeData::PartOfObstacle(mpi) => is_locally_concave(mpi, &features.obstacles),
            //         NodeData::PartOfWater(_) => return false,
            //         NodeData::Arbitrary(_) => return true,
            //     };
            //     return !is_locally_concave;
            // } else { true };
            return true;
        })
        .collect::<Vec<_>>();

    let node_data_index_map = vertices
        .iter()
        .map(|node_data| (*node_data, graph.add_node(*node_data)))
        .collect::<HashMap<_, _>>();

    let mut nav_graph = NavGraph {
        graph,
        node_data_index_map,
        features: features.clone(),
    };

    println!("Adding visible edges...");
    let before_adding_edges = std::time::Instant::now();
    for (i, vertex) in vertices.clone().iter().enumerate() {
        print!("\r{}/{}       ", i, vertices.len() - 1);
        add_visible_edges(
            vertex,
            &mut vertices,
            &mut nav_graph,
            dgc.clone(),
            optimization_mode,
        );
    }
    let duration = before_adding_edges.elapsed();
    println!(
        "\nAdding visible edges... done. Took {}ms",
        duration.as_millis()
    );

    return (nav_graph, duration);
}


pub fn add_coord_to_nav_graph(
    coord: Coordinate<f64>,
    nav_graph: &mut NavGraph,
    dgc: DebugGeometryCallback,
    optimization_mode: VisibilityOptimizationMode,
) -> (NodeData, NodeIndex) {
    let mut vertices = nav_graph.features.iter().collect::<Vec<_>>();

    nav_graph.features.arbitrary.push(OrderedCoordinate(coord));
    let p: NodeData = NodeData::Arbitrary(nav_graph.features.arbitrary.len() - 1);
    let p_index = nav_graph.graph.add_node(p);
    nav_graph.node_data_index_map.insert(p, p_index);
    add_visible_edges(&p, &mut vertices, nav_graph, dgc, optimization_mode);

    return (p, p_index);
}
