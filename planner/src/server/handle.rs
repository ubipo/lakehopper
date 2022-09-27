use std::error::Error;

use derive_more::Display;
use futures::{SinkExt, StreamExt};
use geo::{LineString, MultiPolygon, Point};
use tokio::{sync::mpsc::{self, Sender}, net::TcpStream};
use tokio_tungstenite::{accept_async, tungstenite::Message as WsMessage};

use crate::{
    crs::create_to_int_proj,
    geo_geojson::{geometry_to_feature, multi_polygon_to_feature},
    geo_io::load_gpkg_multi_polygon,
    server::server_msg::ServerMessage,
    nav_graph::{
        add_coord_to_nav_graph, create_nav_graph, nav_graph_to_feature_collection,
        graph_types::{NavGraph, Features}, plan_path_or_recharge, calculate_shortest_path_between_coords,
    }, dgc::create_dgc,
};

use super::{
    client_msg::{ClientMessage, PlanClientMsg},
    server_msg::{ShortestPath, NavGraphLoaded},
};


#[derive(Debug, Default)]
struct UiContext {
    maybe_waters: Option<MultiPolygon<f64>>,
    maybe_obstacles: Option<MultiPolygon<f64>>,
    nav_graph: Option<NavGraph>,
}

#[derive(Debug, Clone, Display)]
struct UnknownClientMessageTypeError(String);
impl Error for UnknownClientMessageTypeError {}

#[derive(Debug, Clone, Display)]
struct WebsocketMessageNotTextError(WsMessage);
impl Error for WebsocketMessageNotTextError {}

const EMPTY_MULTI_POLYGON: geo::MultiPolygon<f64> = geo::MultiPolygon(vec![]);

async fn handle_client_msg(
    message: ClientMessage,
    ui_context: &mut UiContext,
    server_msg_tx_ch: Sender<ServerMessage>,
) -> Result<(), Box<dyn Error + Send + Sync>> {
    match message {
        ClientMessage::MapReady => {
            println!("Map ready");
            let obstacles = match &ui_context.maybe_obstacles {
                Some(obstacles) => obstacles.clone(),
                None => {
                    // let path = "data/iv-grb/small.gpkg";
                    // let name = "small";
                    // let path = "data/iv-grb/medium.gpkg";
                    // let name = "medium";
                    // let path = "data/iv-grb/sv-edegem.gpkg";
                    // let name = "sv-edegem";
                    // let path = "data/iv-grb/processed.gpkg";
                    // let name = "processed";
                    // let path = "data/iv-grb/grb-sv-phd.gpkg";
                    // let name = "grb-sv-phd";
                    // let path = "data/iv-grb/grb-sv-phd-cross-edge-test.gpkg";
                    // let name = "grb-sv-phd-cross-edge-test";
                    // let path = "data/iv-grb/perf-34.gpkg";
                    // let name = "perf-34";
                    let path = "data/iv-grb/sv-zaventem.gpkg";
                    let name = "sv-zaventem";
                    let obstacles = load_gpkg_multi_polygon(path, name).await?;
                    ui_context.maybe_obstacles = Some(obstacles.clone());
                    obstacles
                }
            };
            let obstacles_feature = multi_polygon_to_feature(obstacles);
            server_msg_tx_ch
                .send(ServerMessage::Obstacles(obstacles_feature))
                .await?;
        }
        ClientMessage::LoadWaters => {
            let waters = match &ui_context.maybe_waters {
                Some(waters) => waters.clone(),
                None => {
                    // let path = "data/osm-water/water-small.gpkg";
                    // let name = "water-small";
                    // let path = "data/osm-water/water.gpkg";
                    // let name = "water";
                    // let path = "data/osm-water/water-sv-edegem-II.gpkg";
                    // let name = "water-sv-edegem-II";
                    // let path = "data/osm-water/water-sv-phd.gpkg";
                    // let name = "water-sv-phd";
                    // let path = "data/osm-water/water-sv-phd-diff.gpkg";
                    // let name = "water-sv-phd-diff";
                    // let path = "data/osm-water/water-sv-phd-diff-cross-edge-test.gpkg";
                    // let name = "water-sv-phd-diff-cross-edge-test";
                    // let path = "data/osm-water/pe.gpkg";
                    // let name = "pe";
                    let path = "data/osm-water/sv-zaventem.gpkg";
                    let name = "sv-zaventem";
                    let waters = load_gpkg_multi_polygon(path, name).await?;
                    ui_context.maybe_waters = Some(waters.clone());
                    waters
                }
            };
            // Poles of inaccessibility
            // let pois = waters.iter().filter_map(|water| {
            //     let poi = polylabel(water, &0.1).unwrap();
            //     let distance = poi.euclidean_distance(water.exterior());
            //     Some(poi)
            //     // if distance > 20 {
            //     //     Some(poi)
            //     // } else { None }
            // });
            // let pois_feature = feature_from_points(pois);
            let waters_feature = multi_polygon_to_feature(waters);
            server_msg_tx_ch
                .send(ServerMessage::Waters(waters_feature))
                .await?;
            // server_msg_tx_ch
            //     .send(ServerMessage::Waters(Waters {
            //         waters: waters_feature,
            //         pois: pois_feature,
            //     }))
            //     .await?;
        }
        ClientMessage::LoadRestrictedAirspace => {
            let path = "data/droneguide/restricted-airspace.gpkg";
            let name = "restricted-airspace";
            let restricted_airspace = load_gpkg_multi_polygon(path, name).await?;
            let restricted_airspace_feature = multi_polygon_to_feature(restricted_airspace);
            server_msg_tx_ch
                .send(ServerMessage::RestrictedAirspace(restricted_airspace_feature))
                .await?;
        }
        ClientMessage::VisibilityGraph { visibility_optimization_mode } => {
            let obstacles = ui_context.maybe_obstacles.as_ref().ok_or(
                "Obstacles loaded yet. Please load the obstacles first.",
            )?;
            let waters_default = &EMPTY_MULTI_POLYGON;
            let waters = ui_context.maybe_waters.as_ref().unwrap_or(waters_default);
            let features = Features {
                obstacles: obstacles.clone(),
                waters: waters.clone(),
                arbitrary: Vec::new(),
            };

            let dgc = create_dgc(server_msg_tx_ch.clone());

            // for _ in 0..9 {
            //     create_nav_graph(&features, Some(dgc.clone()), visibility_optimization_mode);
            // }

            let (nav_graph, duration) = create_nav_graph(&features, Some(dgc), visibility_optimization_mode);
            let graph_feature_collection = nav_graph_to_feature_collection(&nav_graph);
            ui_context.nav_graph = Some(nav_graph);
            server_msg_tx_ch
                .send(ServerMessage::NavGraph(NavGraphLoaded::new(graph_feature_collection, duration.as_millis())))
                .await?;
        }
        ClientMessage::CalcPath { start: start_lat_lng, end: end_lat_lng, visibility_optimization_mode } => {
            let nav_graph = ui_context.nav_graph.as_mut().ok_or(
                "Nav graph not loaded yet. Please load the nav graph first.",
            )?;

            let maybe_astar_result = calculate_shortest_path_between_coords(
                nav_graph,
                start_lat_lng.into(),
                end_lat_lng.into(),
                visibility_optimization_mode
            );
            let shortest_path: Option<ShortestPath> = if let Some(astar_result) = maybe_astar_result
            {
                let (cost_edge_data, node_indices) = astar_result;
                let distance = cost_edge_data.length;
                let path_geometry = LineString(
                    node_indices
                        .iter()
                        .map(|&node_index| {
                            let node_data = &nav_graph.graph.node_weight(node_index).unwrap();
                            nav_graph.features.coord(node_data)
                        })
                        .collect::<Vec<_>>(),
                );
                let path_feature = geometry_to_feature(path_geometry.into());
                Some(ShortestPath::new(path_feature, distance))
            } else {
                None
            };
            server_msg_tx_ch
                .send(ServerMessage::ShortestPathCalculated(shortest_path))
                .await?
        }
        ClientMessage::Plan(PlanClientMsg {
            start: start_lat_lng, end: end_lat_lng,
            max_distance_initially, max_distance_after_charge,
            visibility_optimization_mode
        }) => {
            let nav_graph = ui_context.nav_graph.as_mut().ok_or(
                "Nav graph not loaded yet. Please load the nav graph first.",
            )?;

            let dgc = create_dgc(server_msg_tx_ch.clone());

            // Projection needs to be in a separate scope because `proj::Proj`
            // is `!Send`.
            let (start_coord, end_coord) = {
                let proj = create_to_int_proj();
                (
                    proj.project(start_lat_lng.into(), false)?,
                    proj.project(end_lat_lng.into(), false)?,
                )
            };
            let (_, start_index) = add_coord_to_nav_graph(start_coord, nav_graph, None, visibility_optimization_mode);
            let (_, end_index) = add_coord_to_nav_graph(end_coord, nav_graph, None, visibility_optimization_mode);
            let planner_legs = plan_path_or_recharge(
                &nav_graph,
                max_distance_initially,
                max_distance_after_charge,
                start_index,
                end_index,
                Some(dgc)
            )?;
            let planner_legs_geometries = planner_legs
                .iter()
                .map(|(last_reachable_coord, leg_path)| {
                    let leg_path_geometry = LineString(
                        leg_path
                            .iter()
                            .map(|(node_index, _)| {
                                let node_data = &nav_graph.graph.node_weight(*node_index).unwrap();
                                nav_graph.features.coord(node_data)
                            })
                            .collect::<Vec<_>>(),
                    );
                    [
                        geometry_to_feature(Point(*last_reachable_coord).into()),
                        geometry_to_feature(leg_path_geometry.into())
                    ]
                })
                .collect::<Vec<_>>();
            server_msg_tx_ch.send(ServerMessage::PlannerPathCalculated(planner_legs_geometries)).await?;
        }
    }
    Ok(())
}

enum WsMessageResult {
    Handled,
    Close,
}

async fn handle_ws_msg(
    ws_msg: WsMessage,
    ui_context: &mut UiContext,
    ws_tx_ch: Sender<WsMessage>,
) -> Result<WsMessageResult, Box<dyn Error + Send + Sync>> {
    match ws_msg {
        WsMessage::Text(msg_str) => {
            let client_msg = serde_json::from_str(&msg_str)?;
            let (server_msg_tx_ch, mut server_msg_rx_ch) = mpsc::channel::<ServerMessage>(10);
            tokio::spawn(async move {
                while let Some(server_msg) = server_msg_rx_ch.recv().await {
                    ws_tx_ch
                        .send(server_msg.into())
                        .await?;
                }
                Ok::<(), Box<dyn Error + Send + Sync>>(())
            });
            handle_client_msg(client_msg, ui_context, server_msg_tx_ch).await?;
            Ok(WsMessageResult::Handled)
        }
        WsMessage::Close(_) => Ok(WsMessageResult::Close),
        WsMessage::Ping(ping_payload) => {
            ws_tx_ch.send(WsMessage::Pong(ping_payload)).await?;
            Ok(WsMessageResult::Handled)
        }
        _ => Err(Box::new(WebsocketMessageNotTextError(ws_msg)))
    }
}

pub async fn handle_tcp_stream(stream: TcpStream) -> Result<(), Box<dyn Error>> {
    let websocket = accept_async(stream).await?;
    let (mut ws_tx_ch, mut ws_rx_ch) = websocket.split();
    let (ws_proxy_tx_ch, mut ws_proxy_rx_ch) = mpsc::channel::<WsMessage>(10);
    
    tokio::spawn(async move {
        let ui_context = &mut UiContext::default();
        while let Some(Ok(ws_msg)) = ws_rx_ch.next().await {
            match handle_ws_msg(ws_msg, ui_context, ws_proxy_tx_ch.clone()).await {
                Ok(WsMessageResult::Handled) => {}
                Ok(WsMessageResult::Close) => break,
                Err(e) => {
                    let err_str = format!("{:?}", &e);
                    println!("Error handling ws client msg: {}", e);
                    if let Err(_) = ws_proxy_tx_ch.send(ServerMessage::Error(err_str).into()).await {
                        println!("receiver dropped");
                        return;
                    }
                }
            }
        }
    });

    while let Some(ws_msg) = ws_proxy_rx_ch.recv().await {
        ws_tx_ch
            .send(ws_msg)
            .await?;
    }

    Ok(())
}
