"""Build or audit the five small, deterministic BatteryWala catalogues.

The generated files are runtime data. This script is retained so the conversion is
repeatable and every manually curated row keeps its source URL.
"""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "app" / "data"
OUTPUT = DATA / "brands"
BRANDS = {
    "exide": "EXIDE",
    "amaron": "AMARON",
    "amron": "AMARON",
    "sf sonic": "SF SONIC",
    "powerzone": "POWER ZONE",
    "power zone": "POWER ZONE",
    "tata green": "TATA GREEN",
}
FILES = {
    "EXIDE": "exide.json", "AMARON": "amaron.json", "SF SONIC": "sf-sonic.json",
    "POWER ZONE": "power-zone.json", "TATA GREEN": "tata-green.json",
}
SOURCES = {
    "EXIDE": ["https://www.exidecare.com/find-your-battery"],
    "AMARON": ["https://www.amaron.com/battery-finder"],
    "POWER ZONE": ["https://www.powerzoneworld.com/wp-content/uploads/2025/06/Application-Chart-PowerZone-Website.pdf"],
    "SF SONIC": ["https://www.exideindustries.com/international-business/mobility-export-batteries/sf-sonic.aspx"],
    "TATA GREEN": ["https://www.tatagreenbattery.com/wp-content/uploads/2025/02/Tata_Green_Batteries_Online_Warranty_Manual.pdf"],
}

def key(value):
    return re.sub(r"[^a-z0-9]+", " ", str(value or "").lower()).strip()

def brand(value):
    return BRANDS.get(key(value))

def compact_product(row, default_application="vehicle"):
    item = {
        "application": row.get("application") or default_application,
        "model_no": str(row.get("model_no") or "").strip(),
    }
    mapping = {"capacity_ah": "capacity_ah", "voltage": "voltage", "warranty": "warranty",
               "mrp": "tentative_price", "source_url": "source_url", "price_as_of": "price_as_of"}
    for source, target in mapping.items():
        if row.get(source) not in (None, ""):
            item[target] = row[source]
    if item.get("tentative_price") is not None and not item.get("price_as_of"):
        item["price_as_of"] = "legacy source; verify before sale"
    return item

def curated_products():
    sf_source = "https://www.scribd.com/document/861370706/SF-SONIC-Vehicular-Price-List-wef-01-04-2025"
    sf = [
        ("four_wheeler", "72S-35R/L", 35, 4471, "36F+36P"),
        ("four_wheeler", "72S-55LS", 45, 7519, "36F+36P"),
        ("four_wheeler", "72S-DIN74L", 74, 11408, "36F+36P"),
        ("four_wheeler", "72S-DIN100L", 100, 18910, "36F+36P"),
        ("four_wheeler", "66S-40B20R/L", 35, 4373, "33F+33P"),
        ("four_wheeler", "66S-38B20R/L", 35, 4177, "33F+33P"),
        ("four_wheeler", "66S-40LBH/RBH", 40, 4878, "33F+33P"),
        ("three_wheeler", "24S-32R", 32, 3303, "24F"),
        ("commercial_vehicle", "24S-40L", 35, 3788, "24F"),
        ("commercial_vehicle", "24S-60L/R", 60, 5550, "24F"),
        ("commercial_vehicle", "42S-80R", 80, 7260, "24F+18P"),
        ("commercial_vehicle", "42S-88L", 88, 7862, "24F+18P"),
        ("commercial_vehicle", "42S-100R", 100, 9137, "24F+18P"),
        ("commercial_vehicle", "42S-100H29R", 100, 8659, "24F+18P"),
        ("commercial_vehicle", "42S-130R", 130, 11420, "24F+18P"),
        ("commercial_vehicle", "42S-150R", 150, 14750, "24F+18P"),
        ("commercial_vehicle", "42S-180R", 180, 16720, "24F+18P"),
    ]
    sf_rows = [{"application": a, "model_no": m, "capacity_ah": ah, "voltage": 12,
                "tentative_price": price, "price_as_of": "2025-04-01",
                "warranty": warranty, "source_url": sf_source} for a, m, ah, price, warranty in sf]

    tata_source = SOURCES["TATA GREEN"][0]
    # Model families and warranty are from Tata Green's official warranty manual.
    tata = [
        ("two_wheeler", m) for m in ("TG2.5D", "YTZ4-H", "YTZ4", "YTZ5", "YTZ6V-H", "YT5A",
                                     "YTZ7", "YTZ7-H", "TG7D", "YTZ9", "TG9D", "YTZ10S",
                                     "YTZ14S", "YB14L-A2", "GYZ20L")
    ] + [
        ("four_wheeler", m) for m in ("M-42 PREMIO ISS", "36B19L PREMIO", "36B20L PREMIO",
                                      "34B19L PREMIO", "34B20L PREMIO", "40B20R PREMIO",
                                      "40B20L PREMIO", "55D23L PREMIO", "55B24L PREMIO",
                                      "DIN44 PREMIO", "DIN50 PREMIO", "DIN60 PREMIO",
                                      "DIN65 PREMIO", "DIN75 PREMIO", "DIN80 PREMIO",
                                      "DIN100 PREMIO", "70D26 PREMIO", "70D23 PREMIO",
                                      "80D31 PREMIO", "SLV600", "SLV800", "SLV900", "SLV1000")
    ] + [
        ("commercial_vehicle", m) for m in ("38B20", "70D26", "80D31", "105E41", "135G51",
                                            "150G51", "130F51 ROADSTAR", "180H52 ROADSTAR")
    ] + [("generator", "105E41 GENSTAR"), ("tractor", "75D31"), ("tractor", "95E41")]
    tata_rows = [{"application": a, "model_no": m, "voltage": 12,
                  "warranty": "Refer to official model warranty table", "source_url": tata_source}
                 for a, m in tata]
    tata_shop = "https://www.tatagreenbattery.com/batteries-for-car-muv-suv/"
    current_tata = [
        ("TG550R",54,5011,"12F+12P"),("TGX 400L",35,3759,"18F+18P"),
        ("SLV600R",55,5942,"24F+24P"),("SLV DIN60L",60,6866,"18F+18P"),
        ("TG400L",35,3835,"12F+12P"),("SLV DIN65L",65,7459,"18F+18P"),
        ("SLV DIN50R",50,5861,"18F+18P"),("SLV DIN50L",50,5861,"18F+18P"),
        ("SLV DIN44L",44,5447,"18F+18P"),("SLV DIN44R",44,5447,"18F+18P"),
        ("PREMIO 70D23R-BH",68,6697,"24F+36P"),("PREMIO 55D23L",54,5723,"24F+36P"),
        ("PREMIO 55B24L (T1)",45,6146,"30F+36P"),("PREMIO M-42 ISS",38,4460,"24F+36P"),
        ("PREMIO 70D23L-BH",68,6697,"24F+36P"),("PREMIO 40B20L PR3036",35,4442,"30F+36P"),
        ("PREMIO 40B20R PR3036",35,4442,"30F+36P"),("PREMIO 40B20L PR2436",35,4099,"24F+36P"),
        ("PREMIO 40B20R PR2436",35,4099,"24F+36P"),("TG550L",54,5011,"12F+12P"),
        ("PREMIO 70D26R PR3036",70,7780,"30F+36P"),("PREMIO 70D26L PR3036",70,7780,"30F+36P"),
        ("PREMIO 40B20L BH",35,4863,"30F+36P"),("PREMIO 40B20R BH",35,4863,"30F+36P"),
        ("PREMIO 55B24LS",45,7270,"30F+36P"),("PREMIO 70D26R PR2436",65,7343,"24F+36P"),
        ("PREMIO 80D31L",80,8011,"24F+36P"),("PREMIO 36B19L-AM",32,3878,"24F+36P"),
        ("PREMIO 80D31R",80,8011,"24F+36P"),
    ]
    tata_rows.extend({"application":"four_wheeler","model_no":model,"capacity_ah":ah,"voltage":12,
                      "tentative_price":price,"price_as_of":"2026-09-07","warranty":warranty,
                      "source_url":tata_shop} for model,ah,price,warranty in current_tata)
    return {"SF SONIC": sf_rows, "TATA GREEN": tata_rows}

def main():
    legacy_fitments=DATA / "fitments.json"
    if not legacy_fitments.exists():
        paths=sorted(OUTPUT.glob("*.json"))
        names={json.loads(path.read_text(encoding="utf-8"))["brand"] for path in paths}
        if names != set(FILES):raise SystemExit("The five-brand catalogue is incomplete.")
        for path in paths:
            data=json.loads(path.read_text(encoding="utf-8"))
            print(f"{data['brand']}: {len(data['products'])} products, {len(data['fitments'])} fitments")
        return
    payloads = {name: {"schema_version": "3.0", "brand": name,
                       "source_urls": SOURCES[name], "products": [], "fitments": []}
                for name in FILES}
    for path in sorted((DATA / "catalogs").glob("*.json")):
        source = json.loads(path.read_text(encoding="utf-8"))
        for row in source.get("records", []):
            name = brand(row.get("brand"))
            if name and row.get("source_type") != "scrap" and row.get("model_no"):
                payloads[name]["products"].append(compact_product(row))

    old = json.loads(legacy_fitments.read_text(encoding="utf-8"))["fitments"]
    canonical = {}
    for row in old:
        canonical.setdefault((row["application"], key(row["vehicle_model"]), key(row.get("fuel_type"))), set()).add(row["vehicle_make"])
    for row in old:
        for battery in row.get("batteries", []):
            name = brand(battery.get("brand"))
            if not name:
                continue
            make = row["vehicle_make"]
            # The source chart accidentally placed many Yamaha models beneath YEZDI.
            candidates = canonical.get((row["application"], key(row["vehicle_model"]), key(row.get("fuel_type"))), set())
            if key(make) == "yezdi" and any(key(candidate) == "yamaha" for candidate in candidates):
                make = next(candidate for candidate in candidates if key(candidate) == "yamaha")
            payloads[name]["fitments"].append({
                "application": row["application"], "vehicle_make": make,
                "vehicle_model": row["vehicle_model"], "fuel_type": row.get("fuel_type"),
                "model_no": battery["model_no"], "capacity_ah": battery.get("capacity_ah")})

    for name, rows in curated_products().items():
        payloads[name]["products"].extend(rows)

    OUTPUT.mkdir(parents=True, exist_ok=True)
    for name, data in payloads.items():
        known={(key(row["application"]),key(row["model_no"])) for row in data["products"]}
        for fitment in data["fitments"]:
            product_key=(key(fitment["application"]),key(fitment["model_no"]))
            if product_key in known:continue
            data["products"].append({"application":fitment["application"],"model_no":fitment["model_no"],
                                     "capacity_ah":fitment.get("capacity_ah"),"source_url":SOURCES[name][0]})
            known.add(product_key)
        products = {key((row["application"], row["model_no"])): row for row in data["products"]}
        fitments = {key((row["application"], row["vehicle_make"], row["vehicle_model"],
                         row.get("fuel_type"), row["model_no"])): row for row in data["fitments"]}
        data["products"] = sorted(products.values(), key=lambda row: (row["application"], key(row["model_no"])))
        data["fitments"] = sorted(fitments.values(), key=lambda row: (row["application"], key(row["vehicle_make"]), key(row["vehicle_model"])))
        (OUTPUT / FILES[name]).write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        print(f"{name}: {len(data['products'])} products, {len(data['fitments'])} fitments")

if __name__ == "__main__":
    main()
