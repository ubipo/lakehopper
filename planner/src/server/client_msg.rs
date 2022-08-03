use serde::Deserialize;

use crate::nav_graph::VisibilityOptimizationMode;

use super::common::LatLng;

#[derive(Debug, Clone, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct PlanClientMsg {
    pub start: LatLng,
    pub end: LatLng,
    pub max_distance_initially: f64,
    pub max_distance_after_charge: f64,
    pub visibility_optimization_mode: VisibilityOptimizationMode,
}

#[derive(Debug, Clone, Deserialize)]
#[serde(tag = "type", content = "data")]
#[serde(rename_all = "kebab-case")]
pub enum ClientMessage {
    MapReady,
    LoadWaters,
    LoadRestrictedAirspace,
    #[serde(rename_all = "camelCase")]
    VisibilityGraph {
        
        visibility_optimization_mode: VisibilityOptimizationMode
    },
    #[serde(rename_all = "camelCase")]
    CalcPath {
        start: LatLng, end: LatLng,
        visibility_optimization_mode: VisibilityOptimizationMode
    },
    Plan(PlanClientMsg),
}
