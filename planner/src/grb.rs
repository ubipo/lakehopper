//! Handling of Informatie Vlaanderen GRB data
//!
//! See: https://overheid.vlaanderen.be/informatie-vlaanderen/producten-diensten/basiskaart-vlaanderen-grb

use std::{
    fs::{self, File},
    io::{Cursor, Error, Read},
};

use geo::{Geometry, MultiPolygon};
use geos::Geom;
use proj::{Proj, Transform};
use shapefile::ShapeReader;

use crate::crs::ETRS_CRS;

static GRB_CRS: &str = "EPSG:31370";
// Based on European Commission Implementing Regulation 2019/947
// for self-build (no class) / A3 drone
static BUILDING_BUFFER: f64 = 150.0 + 10.; // In CALC_CRS units (probably metres)

pub fn grb_zips_to_residential_geometry_first() -> Result<MultiPolygon<f64>, Error> {
    let grb_to_calc_proj = Proj::new_known_crs(&GRB_CRS, &ETRS_CRS, None).unwrap();
    let mut merged_geometry: geos::Geometry = MultiPolygon::new(Vec::new()).try_into().unwrap();

    let mut done: u16 = 0;

    let before_all_start = std::time::Instant::now();

    let dir = fs::read_dir("./data/iv-grb")?;
    for entry in dir {
        let path = entry.as_ref().unwrap().path();
        if !path
            .file_name()
            .unwrap()
            .to_str()
            .unwrap()
            .ends_with("_Shapefile.zip")
        {
            continue;
        }
        let file = match File::open(&path) {
            Err(error) => {
                if error.kind() == std::io::ErrorKind::IsADirectory {
                    continue;
                }
                return Err(error);
            }
            Ok(f) => f,
        };

        if done == 5 {
            break;
        };
        done += 1;

        println!("Processing {:?}", &path);
        let before_processing_start = std::time::Instant::now();

        let mut archive = zip::ZipArchive::new(file)?;
        let filenames: Vec<String> = archive.file_names().map(|s| s.into()).collect();
        let shp_filename = filenames
            .iter()
            .find(|filename| filename.starts_with("Shapefile/") && filename.ends_with(".shp"))
            .unwrap();
        let base_filename = shp_filename.trim_end_matches(".shp");
        let shp_file = archive.by_name(shp_filename)?;
        let shp_buff = Cursor::new(shp_file.bytes().try_collect::<Vec<u8>>()?);
        let shx_file = archive.by_name(&(base_filename.to_owned() + ".shx"))?;
        let shx_buff = Cursor::new(shx_file.bytes().try_collect::<Vec<u8>>()?);
        let dbf_file = archive.by_name(&(base_filename.to_owned() + ".dbf"))?;
        let dbf_buff = Cursor::new(dbf_file.bytes().try_collect::<Vec<u8>>()?);

        let shape_reader = ShapeReader::with_shx(shp_buff, shx_buff).unwrap();
        let dbase_reader = shapefile::dbase::Reader::new(dbf_buff).unwrap();
        let mut shapefile_reader = shapefile::Reader::new(shape_reader, dbase_reader);

        for shape_record in shapefile_reader.iter_shapes_and_records() {
            let (shape, _record) = shape_record.unwrap();
            let geo_geom = Geometry::<f64>::try_from(shape).unwrap();
            let mut geo_polygon = MultiPolygon::try_from(geo_geom).unwrap();
            geo_polygon.transform(&grb_to_calc_proj).unwrap();
            let geos_geom: geos::Geometry = geo_polygon.clone().try_into().unwrap();
            let buffered = geos_geom.buffer(BUILDING_BUFFER, 2).unwrap();

            merged_geometry = merged_geometry.union(&buffered).unwrap();
        }

        println!("Took: {:.2?}", before_processing_start.elapsed());
    }

    println!("All: {:.2?}", before_all_start.elapsed());

    let mut geometry: Geometry<f64> = merged_geometry.try_into().unwrap();
    return Ok(MultiPolygon::new(Vec::new()));
}
