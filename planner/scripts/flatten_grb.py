from pathlib import Path
from zipfile import ZipFile

OUT_DIR = Path("flat")
OUT_DIR.mkdir(exist_ok=True)

for zip_file_path in Path(".").glob("*_Shapefile.zip"):
    if not zip_file_path.is_file():
        continue
    with ZipFile(zip_file_path, 'r') as zip:
        shp_file = [
            f for f in zip.filelist
            if f.filename.endswith(".shp") and f.filename.startswith("Shapefile/")
        ][0]
        shx_file = [
            f for f in zip.filelist
            if f.filename.endswith(".shx") and f.filename.startswith("Shapefile/")
        ][0]
        dbf_file = [
            f for f in zip.filelist
            if f.filename.endswith(".dbf") and f.filename.startswith("Shapefile/")
        ][0]
        def extract_file(file):
            with zip.open(file) as f:
                internal_path = Path(file.filename)
                with open(OUT_DIR / internal_path.name, "wb") as out:
                    out.write(f.read())
        extract_file(shp_file)
        extract_file(shx_file)
        extract_file(dbf_file)
        
