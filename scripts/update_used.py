import json, os
p = os.path.join(os.environ.get("FASTLIS_BASE", os.path.expanduser("~/workspace/fastlis-content")), "data/used_images.json")
d = json.load(open(p))
# used 21/29 >= 20 -> reset pool run ini
d["used"] = []
d["today_carousel"] = ["lab14.jpg", "dashboard.webp", "lab23.jpg", "lab25.jpg", "tech2.jpg"]
d["last_run"] = "2026-09-15"
d["used"] = sorted(set(d["used"]) | set(d["today_carousel"]))
json.dump(d, open(p, "w"), indent=2)
print("OK used:", d["used"])
