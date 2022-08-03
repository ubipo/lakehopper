use geo::{LineString, Coordinate, prelude::EuclideanDistance};
use proj::Coord;

pub fn line_string_point_at_length(line_string: LineString<f64>, length: f64) -> Option<Coordinate<f64>> {
    let mut accumulated_length = 0.0;
    let (line_containing_point, line_containing_point_length) = line_string.lines()
        .find_map(|line| {
            let line_length = line.start.euclidean_distance(&line.end);
            let length_to_line_end = accumulated_length + line_length;
            if length_to_line_end >= length {
                return Some((line, line_length));
            }
            accumulated_length = length_to_line_end;
            return None;
        })?;
    let point_distance_along_line = length - accumulated_length;
    let line_point_ratio = point_distance_along_line / line_containing_point_length;
    return Some(Coordinate::from_xy(
        (1.0 - line_point_ratio) * line_containing_point.start.x + line_point_ratio * (line_containing_point.end.x),
        (1.0 - line_point_ratio) * line_containing_point.start.y + line_point_ratio * (line_containing_point.end.y)
    ));
}
