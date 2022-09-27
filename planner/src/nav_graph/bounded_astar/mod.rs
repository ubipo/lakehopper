//! Algorithm and auxiliary functions to recharging.

mod scored;

use std::{
    collections::{BinaryHeap, HashMap, hash_map::Entry::{Occupied, Vacant}},
    hash::Hash,
};

use petgraph::{
    visit::{IntoEdges, Visitable, GraphBase, EdgeRef},
    algo::Measure,
    
};

pub use self::scored::MinScored;

pub enum IsGoalResult {
    /// Indicates the node being considered for visiting is outside the maximum
    /// allowed range. Treat this node as being a dead end (do not explore
    /// further).
    MaximumExtend,
    /// Indicates the goal node has been reached. Stop the search.
    Goal,
    /// Not a goal and within the maximum allowed range; continue.
    NotGoal,
}

/// Modified version of `petgraph::algo::astar` with the possibility to indicate
/// the reason to end the search (in more detail than just 'the goal is
/// reached'), as well as to base this decision on the current estimate score.
/// 
/// The reason for ending the search is returned.
pub fn bounded_astar<G, F, H, K, IsGoal>(
    graph: G,
    start: G::NodeId,
    mut is_goal: IsGoal,
    mut edge_cost: F,
    mut estimate_cost: H,
) -> (Option<(K, Vec<(G::NodeId, K)>)>, ScoredPathTracker<G, K>)
where
    G: IntoEdges + Visitable,
    // Modification from original: also provide access to current estimate score
    IsGoal: FnMut(G::NodeId, K) -> IsGoalResult,
    G::NodeId: Eq + Hash,
    F: FnMut(G::EdgeRef) -> K,
    H: FnMut(G::NodeId) -> K,
    K: Measure + Copy,
{
    let mut visit_next = BinaryHeap::new();
    let mut scores = HashMap::new(); // g-values, cost to reach the node
    let mut estimate_scores = HashMap::new(); // f-values, cost to reach + estimate cost to goal
    let mut path_tracker = ScoredPathTracker::<G, K>::new();

    let zero_score = K::default();
    scores.insert(start, zero_score);
    visit_next.push(MinScored(estimate_cost(start), start));

    while let Some(MinScored(estimate_score, node)) = visit_next.pop() {
        // This lookup can be unwrapped without fear of panic since the node was necessarily scored
        // before adding it to `visit_next`.
        let node_score = scores[&node];

        match is_goal(node, node_score) {
            IsGoalResult::MaximumExtend => continue,
            IsGoalResult::Goal => {
                let path = path_tracker.reconstruct_path_to(node);
                return (Some((node_score, path)), path_tracker);
            }
            IsGoalResult::NotGoal => {},
        }

        match estimate_scores.entry(node) {
            Occupied(mut entry) => {
                // If the node has already been visited with an equal or lower score than now, then
                // we do not need to re-visit it.
                if *entry.get() <= estimate_score {
                    continue;
                }
                entry.insert(estimate_score);
            }
            Vacant(entry) => {
                entry.insert(estimate_score);
            }
        }

        for edge in graph.edges(node) {
            let next = edge.target();
            let next_score = node_score + edge_cost(edge);

            match scores.entry(next) {
                Occupied(mut entry) => {
                    // No need to add neighbors that we have already reached through a shorter path
                    // than now.
                    if *entry.get() <= next_score {
                        continue;
                    }
                    entry.insert(next_score);
                }
                Vacant(entry) => {
                    entry.insert(next_score);
                }
            }

            path_tracker.set_predecessor(next, node, next_score);
            let next_estimate_score = next_score + estimate_cost(next);
            visit_next.push(MinScored(next_estimate_score, next));
        }
    }

    (None, path_tracker)
}

pub struct ScoredPathTracker<G, K>
where
    G: GraphBase,
    G::NodeId: Eq + Hash,
    K: Measure + Copy,
{
    came_from: HashMap<G::NodeId, (G::NodeId, K)>,
}

impl<G, K> ScoredPathTracker<G, K>
where
    G: GraphBase,
    G::NodeId: Eq + Hash,
    K: Measure + Copy,
{
    fn new() -> ScoredPathTracker<G, K> {
        ScoredPathTracker {
            came_from: HashMap::new(),
        }
    }

    fn set_predecessor(&mut self, node: G::NodeId, previous: G::NodeId, score: K) {
        self.came_from.insert(node, (previous, score));
    }

    pub fn reconstruct_path_to(&self, last: G::NodeId) -> Vec<(G::NodeId, K)> {
        let mut path = Vec::new();

        let mut current = last;
        while let Some(&(previous, current_score)) = self.came_from.get(&current) {
            path.push((current, current_score));
            current = previous;
        }
        path.push((current, K::default()));

        path.reverse();

        path
    }
}
