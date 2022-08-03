use geo::Geometry;
use tokio::sync::mpsc::{Sender, channel};

use crate::{geo_geojson::geometry_to_feature, server::ServerMessage};

// Callback to send arbitrary geometry to the UI for debugging purposes.
pub type DebugGeometryCallback = Option<Sender<Geometry<f64>>>;

pub fn create_dgc(server_msg_tx_ch: Sender<ServerMessage>) -> Sender<Geometry<f64>> {
    let (dgc, mut dgc_rx) = channel::<Geometry<f64>>(10);
    let dgc_server_msg_tx_ch = server_msg_tx_ch.clone();
    tokio::spawn(async move {
        while let Some(geometry) = dgc_rx.recv().await {
            let feature = geometry_to_feature(geometry);
            dgc_server_msg_tx_ch
                .send(ServerMessage::DebugGeometries(feature))
                .await
                .unwrap();
        }
    });
    return dgc;
}
