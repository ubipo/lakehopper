#![feature(slice_concat_trait)]
#![feature(iterator_try_collect)]
#![feature(io_error_more)]
#![feature(let_chains)]
#![feature(map_first_last)]
#![feature(once_cell)]
#![feature(box_syntax)]
#![feature(is_some_with)]

extern crate approx;

mod coord_ext;
mod crs;
mod droneguide;
mod geo_geojson;
mod geo_io;
mod grb;
mod intersection;
mod modulo;
mod mpi;
mod multi_polygon_intersection;
mod server;
mod nav_graph;
mod winding;
mod dgc;
mod line_string_ratio;

use std::error::Error;

use server::serve_ui_forever;

#[tokio::main]
async fn main() -> Result<(), Box<dyn Error>> {
    // let bbox = Rect::new(coord! { x: 2.3, y: 49.5}, coord! { x: 6.7, y: 51.5});

    // let conditions = fetch_conditions().await;
    // let geozone_features = fetch_geozones_features(bbox).await;
    // let geozones: Vec<Geozone> = geozone_features.iter().map(
    //     |f| feature_to_geozone(f.clone(), &conditions)
    // ).collect();

    // let serialized = serde_json::to_string(&geozones).unwrap();
    // File::create("data.json").await.unwrap().write_all(
    //     serialized.as_bytes()
    // ).await.unwrap();

    // println!("{:?}", geozones.first().unwrap())

    // geometryType=esriGeometryEnvelope&geometry=2.3,49.5,6.7,51.5

    // let mut core = Core::new().unwrap();
    // let handle = core.handle();

    serve_ui_forever().await?;
    Ok(())

    // ui_main();

    // tauri::Builder::default()
    //     .on_page_load(|window, _ev| {
    //         println!("Window loaded");
    //         let window_clone = window.clone();
    //         window.listen_global("map-ready", move |_event| {
    //             println!("Map ready in window");
    //             ui_main(&window_clone);
    //         });
    //       })
    //     .run(tauri::generate_context!())
    //     .expect("error while running tauri application");
}
