use std::{error::Error, collections::{HashSet, BinaryHeap, BTreeMap, HashMap, hash_map::Entry}};

use geo::{prelude::{EuclideanDistance, ClosestPoint}, Point, LineString, GeometryCollection, Geometry, Coordinate};
use ordered_float::OrderedFloat;
use petgraph::{graph::NodeIndex, algo::astar};
use strum_macros::Display;

use crate::{dgc::DebugGeometryCallback, nav_graph::bounded_astar::{IsGoalResult, MinScored}, mpi::{MpiCoordsIterable, Mpi}, line_string_ratio::line_string_point_at_length};

use super::{NavGraph, Edge, bounded_astar::bounded_astar, NodeData};

enum ReasonToEndRechargeSearch {
    MaxDistanceReached,
    WaterReached(NodeIndex),
}

#[derive(Debug, Display)]
pub enum PlannerError {
    NoPathToEnd,
    NoPathToWater,
    MaxDistanceReached,
    WaterReached(NodeIndex),
}
impl Error for PlannerError {}

pub fn plan_path_or_recharge(
    nav_graph: &NavGraph,
    max_distance_initially: f64,
    max_distance_after_charge: f64,
    start: NodeIndex,
    end: NodeIndex,
    dgc: DebugGeometryCallback,
) -> Result<Vec<(Coordinate<f64>, Vec<(NodeIndex, Edge)>)>, PlannerError> {
    let end_coord = nav_graph.features.coord(nav_graph.graph.node_weight(end).unwrap());
    
    let mut leg_start = start;
    let mut prev_leg_start = leg_start;
    let mut leg_max_distance = max_distance_initially;
    let mut legs = Vec::<(Coordinate<f64>, Vec<(NodeIndex, Edge)>)>::new();

    loop {
        let leg_start_coord = nav_graph.features.coord(nav_graph.graph.node_weight(leg_start).unwrap());

        let (leg_path_to_end_data, _) = bounded_astar(
            &nav_graph.graph,
            leg_start,
            |n, _| if n == end { IsGoalResult::Goal } else { IsGoalResult::NotGoal },
            |e| *e.weight(),
            |node_index| {
                let node_data = nav_graph.graph.node_weight(node_index).unwrap();
                let coord = nav_graph.features.coord(node_data);
                Edge::new(coord.euclidean_distance(&end_coord))
            },
        );
        let (Edge { length: leg_distance_to_end }, leg_path_to_end) = leg_path_to_end_data.ok_or(PlannerError::NoPathToEnd)?;
        println!("leg_distance_to_end: {}", leg_distance_to_end);
        println!("leg_max_distance: {}", leg_max_distance);

        if leg_start == start {
            let path_geometry = LineString(
                leg_path_to_end
                    .iter()
                    .map(|(node_index, _)| {
                        let node_data = &nav_graph.graph.node_weight(*node_index).unwrap();
                        nav_graph.features.coord(node_data)
                    })
                    .collect::<Vec<_>>(),
            );
            dgc.clone().unwrap().try_send(path_geometry.into());
        }

        if leg_distance_to_end <= leg_max_distance {
            println!("Goal reached");
            legs.push((end_coord, leg_path_to_end));
            break;
        }

        let last_reachable_point = line_string_point_at_length(
            LineString::from_iter(leg_path_to_end.iter()
                .map(|(n, _)| nav_graph.features.coord(nav_graph.graph.node_weight(*n).unwrap()))
            ),
            leg_max_distance
        ).unwrap();

        let mut possible_recharge_points = nav_graph.features.waters.indexed_coords_iter()
            .map(|mpi| (mpi, (&nav_graph.features.waters)[&mpi]))
            .filter(|(_, coord)| {
                let leg_start_to_recharge_distance = leg_start_coord.euclidean_distance(coord);
                leg_start_to_recharge_distance <= leg_max_distance
            })
            .collect::<Vec<_>>();
        possible_recharge_points.sort_by_key(|(_, coord)| OrderedFloat(coord.euclidean_distance(&last_reachable_point)));
    
        let (
            best_recharge_point_mpi,
            best_recharge_point_coord,
            best_recharge_point_path,
         ) = possible_recharge_points.iter()
            .find_map(|(recharge_point_mpi, recharge_point_coord)| {
                let (start_to_recharge_point_path_data, _) = bounded_astar(
                    &nav_graph.graph,
                    leg_start,
                    |n, Edge { length: path_length }| {
                        if path_length > max_distance_initially {
                            return IsGoalResult::MaximumExtend;
                        }
    
                        let node_data = nav_graph.graph.node_weight(n).unwrap();
                        if let NodeData::PartOfWater(n_mpi) = node_data {
                            if n_mpi == recharge_point_mpi {
                                return IsGoalResult::Goal;
                            }
                        }
                        return IsGoalResult::NotGoal;
                    },
                    |e| *e.weight(),
                    |node_index| {
                        let node_coord = nav_graph.features.coord(nav_graph.graph.node_weight(node_index).unwrap());
                        Edge::new(node_coord.euclidean_distance(recharge_point_coord))
                    }
                );
                let (_, path_to_charge_point) = start_to_recharge_point_path_data?;
                Some((recharge_point_mpi, recharge_point_coord, path_to_charge_point))
            })
            .ok_or(PlannerError::NoPathToWater)?;

        let best_recharge_point = nav_graph.node_data_index_map[&NodeData::PartOfWater(*best_recharge_point_mpi)];

        legs.push((last_reachable_point, best_recharge_point_path));

        prev_leg_start = leg_start;
        leg_start = best_recharge_point;

        if leg_start == prev_leg_start {
            println!("Loop");
            break;
        }

        leg_max_distance = max_distance_after_charge;
    }

    // for leg in legs {
    //     let leg_geometry = LineString(
    //         leg
    //             .iter()
    //             .map(|(node_index, _)| {
    //                 let node_data = &nav_graph.graph.node_weight(*node_index).unwrap();
    //                 nav_graph.features.coord(node_data)
    //             })
    //             .collect::<Vec<_>>(),
    //     );
    //     dgc.clone().unwrap().try_send(leg_geometry.into());
    // }

    // dgc.clone().unwrap().try_send(Geometry::GeometryCollection(GeometryCollection(reachable_waters.iter().map(|(water_index, _)| {
    //     let water = &nav_graph.features.waters.0[*water_index];
    //     Geometry::Polygon(water.clone())
    // }).collect::<Vec<_>>())));

    // match end_reason {
    //     ReasonToEndRechargeSearch::MaxDistanceReached => {
    //         return Err(PlannerError::MaxDistanceReached);
    //     },
    //     ReasonToEndRechargeSearch::WaterReached(_) => {
    //         let path_geometry = LineString(
    //             shortest_path_to_water
    //                 .iter()
    //                 .map(|(node_index, _)| {
    //                     let node_data = &nav_graph.graph.node_weight(*node_index).unwrap();
    //                     nav_graph.features.coord(node_data)
    //                 })
    //                 .collect::<Vec<_>>(),
    //         );
    //         dgc.unwrap().try_send(path_geometry.into());
    //     },
    // }

    return Ok(legs);
}
