use std::{collections::HashMap, fmt::Display, iter};

use geo::{CoordNum, Geometry, MultiPolygon, Rect};
use geojson::{Feature, FeatureCollection, GeoJson};
use log::warn;
use reqwest::Url;
use serde::{Deserialize, Serialize};

const GEOZONE_URL: &str = "https://services3.arcgis.com/om3vWi08kAyoBbj3/ArcGIS/rest/services/Geozone_Download_Prod/FeatureServer/0/query";
const CONDITION_URL: &str = "https://services3.arcgis.com/om3vWi08kAyoBbj3/ArcGIS/rest/services/Condition_Download_Prod/FeatureServer/0/query";

trait UrlParamDisplay {
    fn url_param_fmt(self) -> String;
}

impl<T: CoordNum + Display> UrlParamDisplay for Rect<T> {
    fn url_param_fmt(self: Rect<T>) -> String {
        let min = self.min();
        let max = self.max();
        return vec![
            min.x.to_string(),
            min.y.to_string(),
            max.x.to_string(),
            max.y.to_string(),
        ]
        .join(",");
    }
}

#[derive(Deserialize, Debug)]
struct ConditionsResponseFeatureAttributes {
    condition_en: String,
    #[serde(rename = "Generieke_categorie_geozone")]
    category: String,
}

#[derive(Deserialize, Debug)]
struct ConditionsResponseFeature {
    attributes: ConditionsResponseFeatureAttributes,
}

#[derive(Deserialize, Debug)]
struct ConditionsResponse {
    features: Vec<ConditionsResponseFeature>,
}

type CategoryConditions = HashMap<String, Vec<String>>;

async fn fetch_conditions() -> CategoryConditions {
    let url = Url::parse_with_params(
        CONDITION_URL,
        &[
            ("f", "pjson"),
            ("Where", "1=1"), // A 'where' condition is obligated; use a dummy as the dataset is small enough to be fetched in its entirety
            ("outFields", "*"), // All fields
        ],
    )
    .unwrap();

    let body: String = reqwest::get(url)
        .await
        .expect("conditions request to be successful")
        .text()
        .await
        .expect("conditions response to have a body");

    let conditions = serde_json::from_str::<ConditionsResponse>(&body)
        .expect("conditions response to be json")
        .features;

    let mut m = CategoryConditions::new();
    for condition in conditions {
        // Category is case-insensitive (see for example EBR57_EEPOEL: Mil R areas)
        let category = condition.attributes.category.to_lowercase();
        let condition_desc = condition.attributes.condition_en;
        m.entry(category)
            .or_insert_with(Vec::new)
            .push(condition_desc);
    }
    return m;
}

#[derive(Deserialize, Debug)]
struct GeozoneProperties {
    name: String,
    lowerLimit: f64,
    upperLimit: f64,
    categories: String,
}

async fn fetch_geozones_features<T: CoordNum + Display>(bbox: Rect<T>) -> Vec<Feature> {
    let url = Url::parse_with_params(
        GEOZONE_URL,
        &[
            ("f", "pgeojson"),
            ("geometryType", "esriGeometryEnvelope"),
            ("geometry", &bbox.url_param_fmt()),
            ("spatialRel", "esriSpatialRelIntersects"), // Areas that intersect the bbox
            ("outFields", "*"),                         // All fields
            ("returnGeometry", "true"),
            ("inSR", "4326"), // WGS84 degrees https://epsg.io/4326
            ("outSR", "4326"),
        ],
    )
    .unwrap();

    let response = reqwest::get(url)
        .await
        .expect("geozone request to be successful");

    // let users: Vec<User> = response.json().await?;
    let body = response
        .text()
        .await
        .expect("geozone response to have a body");
    // println!("{:?}", body);

    let geojson = body
        .parse::<GeoJson>()
        .expect("geozone response to be parsable geoJSON");
    let feature_collection =
        FeatureCollection::try_from(geojson).expect("geozone geoJSON to be a FeatureCollection");

    return feature_collection.features;
    // println!("{:?}", features.features[0].properties.as_ref().expect("feature has properties"));
}

type AMSLHeightMeters = u32;

#[derive(Deserialize, Serialize, Debug)]
struct Geozone {
    name: String,
    lower: AMSLHeightMeters,
    upper: AMSLHeightMeters,
    conditions: Vec<String>,
    geometry: MultiPolygon<f64>,
}

fn feature_to_geozone(feature: Feature, category_conditions: &CategoryConditions) -> Geozone {
    let properties: GeozoneProperties =
        serde_json::from_value(feature.properties.unwrap().try_into().unwrap()).unwrap();
    let geometry = Geometry::try_from(feature.geometry.unwrap().value).unwrap();
    let multi_polygon = match geometry {
        Geometry::MultiPolygon(geometry) => geometry,
        Geometry::Polygon(geometry) => MultiPolygon::from_iter(iter::once(geometry)),
        _ => panic!("expected Polygon or MultiPolygon"),
    };

    let conditions_opt = category_conditions.get(&properties.categories.to_lowercase());
    let conditions = match conditions_opt {
        Some(v) => v.clone(),
        None => {
            warn!("{} has no conditions", properties.name);
            Vec::new()
        }
    };

    Geozone {
        name: properties.name,
        lower: properties.lowerLimit as u32,
        upper: properties.upperLimit.ceil() as u32,
        conditions: conditions,
        geometry: multi_polygon,
    }
}
