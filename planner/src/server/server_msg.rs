use derive_more::Constructor;
use geojson::{Feature, FeatureCollection};
use serde::Serialize;
use tokio_tungstenite::tungstenite::Message as WsMessage;

#[derive(Clone, Debug, Serialize, Constructor)]
pub struct ShortestPath {
    path: Feature,
    distance: f64,
}

// #[derive(Clone, Debug, Serialize, Constructor)]
// pub struct Waters {
//     pub waters: Feature,
//     pub pois: Feature
// }

#[derive(Clone, Debug, Serialize, Constructor)]
pub struct NavGraphLoaded {
    graph: FeatureCollection,
    duration: u128,
}

#[derive(Clone, Debug, Serialize)]
#[serde(tag = "type", content = "data")]
#[serde(rename_all = "kebab-case")]
pub enum ServerMessage {
    Obstacles(Feature),
    Waters(Feature),
    RestrictedAirspace(Feature),
    NavGraph(NavGraphLoaded),
    DebugGeometries(Feature),
    ShortestPathCalculated(Option<ShortestPath>),
    PlannerPathCalculated(Vec<[Feature; 2]>),
    Error(String),
}

impl Into<WsMessage> for ServerMessage {
    fn into(self) -> WsMessage {
        WsMessage::Text(serde_json::to_string(&self).unwrap())
    }
}
