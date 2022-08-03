use std::{collections::HashMap};

use derive_more::{Add, Constructor};
use geo::{Coordinate, MultiPolygon};
use petgraph::{graph::NodeIndex, Graph, Undirected};

use crate::{coord_ext::OrderedCoordinate, mpi::{Mpi, MpiCoordsIterable}};

#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub enum NodeData {
    PartOfWater(Mpi),
    PartOfObstacle(Mpi),
    Arbitrary(usize),
}

#[derive(Debug, Clone, Copy, Default, Constructor, PartialEq, PartialOrd, Add)]
pub struct Edge {
    pub length: f64,
}

#[derive(Debug, Clone)]
pub struct Features {
    pub obstacles: MultiPolygon<f64>,
    pub waters: MultiPolygon<f64>,
    pub arbitrary: Vec<OrderedCoordinate>,
}

impl Features {
    pub fn coord(&self, node_data: &NodeData) -> Coordinate<f64> {
        match node_data {
            NodeData::PartOfWater(mpi) => (&self.waters)[mpi],
            NodeData::PartOfObstacle(mpi) => (&self.obstacles)[mpi],
            NodeData::Arbitrary(i) => self.arbitrary[*i].0,
        }
    }

    pub fn iter(&self) -> Box<dyn Iterator<Item = NodeData> + '_> {
        box self.obstacles.indexed_coords_iter().map(|mpi| NodeData::PartOfObstacle(mpi)).chain(
            self.waters.indexed_coords_iter().map(|mpi| NodeData::PartOfWater(mpi))
        ).chain(
            self.arbitrary.iter().enumerate().map(|(i, _)| NodeData::Arbitrary(i))
        )
    }
}

/// NavGraph contains both a graph as well as a map of node indices to node data
#[derive(Debug, Clone)]
pub struct NavGraph {
    pub graph: Graph<NodeData, Edge, Undirected>,
    pub node_data_index_map: HashMap<NodeData, NodeIndex>,
    pub features: Features,
}
