use geo::{GeometryCollection, Line, MultiPoint, Point};
use geojson::{Feature, FeatureCollection};
use proj::Transform;

use crate::crs::create_to_ext_proj;

use super::graph_types::NavGraph;

pub fn nav_graph_to_feature_collection(
    nav_graph: &NavGraph,
) -> geojson::FeatureCollection {
    let proj = create_to_ext_proj();
    let features = &nav_graph.features;
    let vertices_geom = MultiPoint::from_iter(
        nav_graph.graph
            .node_weights()
            .map(|node_data| Point(features.coord(node_data).transformed(&proj).unwrap())),
    );
    let vertices_feature = Feature::from(geojson::Geometry::from(&vertices_geom));
    let edge_geom = GeometryCollection::from_iter(nav_graph.graph.edge_indices().map(|edge_index| {
        let (start_index, end_index) = nav_graph.graph.edge_endpoints(edge_index).unwrap();
        Line::new(
            features.coord(
                nav_graph.graph.node_weight(start_index).unwrap()
            ).transformed(&proj).unwrap(),
            features.coord(
                nav_graph.graph.node_weight(end_index).unwrap()
            ).transformed(&proj).unwrap(),
        )
    }));
    let edge_feature = Feature::from(geojson::Geometry::from(&edge_geom));
    return FeatureCollection::from_iter([vertices_feature, edge_feature]);
}
