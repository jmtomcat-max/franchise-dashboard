import json, sqlite3, time, getpass
import urllib.parse, urllib.request
from pathlib import Path

ROOT = Path(r"D:\Franchise_Dashboard")
ROOT.mkdir(parents=True, exist_ok=True)
DB = ROOT / "gangnam_food_stores.sqlite3"
URL = "https://apis.data.go.kr/B553077/api/open/sdsc2/storeListInDong"

key = getpass.getpass("API key: ").strip()
if not key:
    raise SystemExit("API key is required")

con = sqlite3.connect(DB)
con.execute("""CREATE TABLE IF NOT EXISTS stores (
    bizes_id TEXT PRIMARY KEY,
    name TEXT, middle_code TEXT, small_code TEXT,
    province TEXT, district TEXT, dong TEXT,
    address TEXT, lat REAL, lon REAL,
    raw_json TEXT
)""")
con.execute("""CREATE TABLE IF NOT EXISTS progress (
    page INTEGER PRIMARY KEY,
    source_month TEXT,
    collected_at TEXT DEFAULT CURRENT_TIMESTAMP
)""")
con.commit()

page = 1
total = None
source_month = None

while True:
    params = {
        "serviceKey": key,
        "divId": "signguCd",
        "key": "11680",
        "indsLclsCd": "I2",
        "numOfRows": 1000,
        "pageNo": page,
        "type": "json"
    }
    url = URL + "?" + urllib.parse.urlencode(params)
    try:
        with urllib.request.urlopen(url, timeout=45) as response:
            result = json.load(response)
        header = result.get("header", {})
        if str(header.get("resultCode")) != "00":
            raise RuntimeError(str(header))
        body = result["body"]
        items = body.get("items") or []
        if isinstance(items, dict):
            items = items.get("item", [])
        if isinstance(items, dict):
            items = [items]
        total = int(body.get("totalCount", 0))
        month = str(header.get("stdrYm", "unknown"))
        if source_month is None:
            source_month = month
            old = con.execute(
                "SELECT DISTINCT source_month FROM progress"
            ).fetchall()
            if old and any(x[0] != month for x in old):
                raise RuntimeError(
                    "Source month changed. Review existing DB first."
                )
        if month != source_month:
            raise RuntimeError("Source month changed during collection")

        if con.execute(
            "SELECT 1 FROM progress WHERE page=?", (page,)
        ).fetchone():
            print("Already collected page", page)
        else:
            with con:
                for s in items:
                    if s.get("indsMclsCd") == "I211":
                        continue
                    if s.get("indsSclsCd") == "I20701":
                        continue
                    if not s.get("bizesId"):
                        continue
                    con.execute(
                        """INSERT OR REPLACE INTO stores VALUES
                        (?,?,?,?,?,?,?,?,?,?,?)""",
                        (
                            s["bizesId"], s.get("bizesNm"),
                            s.get("indsMclsCd"), s.get("indsSclsCd"),
                            s.get("ctprvnNm"), s.get("signguNm"),
                            s.get("adongNm"), s.get("rdnmAdr"),
                            s.get("lat"), s.get("lon"),
                            json.dumps(s, ensure_ascii=False)
                        )
                    )
                con.execute(
                    "INSERT INTO progress(page,source_month) VALUES(?,?)",
                    (page, month)
                )
            print("Saved page", page, "/", total, flush=True)

        if page * 1000 >= total or not items:
            break
        page += 1
        time.sleep(0.4)
    except Exception as e:
        print("Stopped at page", page, ":", e)
        raise
print("Finished. Saved stores:",
      con.execute("SELECT COUNT(*) FROM stores").fetchone()[0])
con.close()
