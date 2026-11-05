"""Build the static dataset for the midterm schedule web app.

Reads every seating-chart PDF (per-student rooms) and the official Fall 2026
midterm schedule (course catalogue), then writes:

  data/students.json   student ID -> [exam, ...]   (seating charts only)
  data/courses.json    17 charted courses -> date / time / title
  data/catalog.json    every course in the official midterm schedule
  data/programmes.json first-year programme -> expected subjects + options
  data/students.js     all of the above, embedded for file:// use
"""
import pdfplumber, glob, os, re, json, sys
from collections import defaultdict

folder = sys.argv[2] if len(sys.argv) > 2 else "."
outdir = sys.argv[1] if len(sys.argv) > 1 else "data"
SCHEDULE_FILES = [
    os.path.join(folder, "Exam_Schedule.pdf"),
]
ROOM_RE = re.compile(r"^[A-Z]{0,2}\d{3}-[A-Z]\d?$")
ID_RE = re.compile(r"^\d{9}$")
SEC_RE = re.compile(r"^\((?:(\d{3})-)?(S\d{2})\)$")
MONTHS = {"JAN": 1, "FEB": 2, "MAR": 3, "APR": 4, "MAY": 5, "JUN": 6,
          "JUL": 7, "AUG": 8, "SEP": 9, "OCT": 10, "NOV": 11, "DEC": 12}
DAYS = ["MONDAY", "TUESDAY", "WEDNESDAY", "THURSDAY", "FRIDAY", "SATURDAY", "SUNDAY"]

TITLES = {
    "CSAI 101": "Fundamentals of Programming",
    "CSAI 111": "Fundamentals of Programming",
    "CSAI 102": "Digital Logic and Computer Architecture",
    "CSAI 112": "Digital Logic and Computer Architecture",
    "CSAI 201": "Data Structures",
    "CSAI 202": "Introduction to Database Systems",
    "CSAI 205": "Fundamentals of Circuits and Electronics",
    "CSAI 252": "Introduction to Computer Networks",
    "CSCI 101": "Introduction to Computer Science",
    "DSAI 203": "Data Integration and Visualization",
    "ENGL 003": "Remedial English 2",
    "ENGL 004": "Remedial English 3",
    "ENGR 102": "Introduction to Engineering Design",
    "ENGR 121": "Engineering Drawing",
    "MATH 101": "Calculus I",
    "MATH 103": "Calculus for Computational Science",
    "MATH 105": "Probability and Statistics",
    "CHEM 103": "Introduction to Chemistry for Engineers",
    "PHYS 105": "Intro to Classical Mechanics for Engineers",
    "SCH 210": "Social Issues",
    "SCH 211": "Professional Ethics and Legal Aspects",
    "SCH 263": "Engineering Ethics and Safety",
}
# lecture course -> lab-section course codes printed in the same seating chart
ALIASES = {
    "CSAI 101": ["CSAI 111"],
    "CSAI 102": ["CSAI 112"],
}
ATTENDANCE_RE = re.compile(r"Room\s+([A-Z0-9]{2,}-[A-Z0-9]\d?)\s*\(\s*\d+\s+students\s*\)")
ATTENDANCE_NAME = re.compile(r"Attendance[_\s-]*Sheet", re.I)


def col_of(x, anchors):
    idx = 0
    for i, a in enumerate(anchors):
        if x >= a - 6:
            idx = i
    return idx


def cluster(xs):
    out = []
    for x in sorted(xs):
        if out and x - out[-1][-1] < 6:
            out[-1].append(x)
        else:
            out.append([x])
    return [round(sum(c) / len(c), 1) for c in out]


def parse_when(hdr):
    m = re.search(r"([A-Z]{3})\s+(\d{1,2})(?:st|nd|rd|th)\s+([A-Z]{3})\s+(\d{2}:\d{2})-(\d{2}:\d{2})", hdr)
    if not m:
        return None
    day, dom, mon, t1, t2 = m.groups()
    return f"2026-{MONTHS[mon]:02d}-{int(dom):02d}", f"{t1}-{t2}", DAYS[[d[:3] for d in DAYS].index(day)]


def parse_day(day_txt):
    """Parse 'SAT 7th NOV' -> (date, weekday name)."""
    m = re.search(r"([A-Z]{3})\s+(\d{1,2})(?:st|nd|rd|th)\s+([A-Z]{3})", day_txt)
    if not m:
        return None
    day, dom, mon = m.groups()
    return f"2026-{MONTHS[mon]:02d}-{int(dom):02d}", DAYS[[d[:3] for d in DAYS].index(day)]


# ---------------------------------------------------------------- seating charts
students = {}
courses = {}

for f in sorted(glob.glob(os.path.join(folder, "*.pdf"))):
    name = os.path.basename(f)
    if name.startswith("Midterm_") or ATTENDANCE_NAME.search(name) or name.startswith("Exam"):
        continue
    with pdfplumber.open(f) as pdf:
        pages = []
        for pno, page in enumerate(pdf.pages, 1):
            words = page.extract_words()
            anchors = cluster({round(w["x0"], 1) for w in words if ID_RE.match(w["text"])})
            rooms = [(w["text"], (w["x0"] + w["x1"]) / 2) for w in words if ROOM_RE.match(w["text"])]
            pages.append({"page": pno, "anchors": anchors, "rooms": rooms, "words": words})

        # header (course / date / time / total) on page 1
        hdr_line = None
        for ln in pdf.pages[0].extract_text_lines(layout=False, strip=True):
            if re.search(r"\d{3,4}\s*students", ln["text"]) and re.match(r"^[A-Z]{2,4}\s?\d{3}", ln["text"]):
                hdr_line = ln["text"].strip()
                break
        fm = re.match(r"^([A-Z]+)_(\d{3})", name)
        code = f"{fm.group(1)} {fm.group(2)}"  # header text can lose its first letter (e.g. "SAI 202")
        when = parse_when(hdr_line)
        title = TITLES.get(code, code)
        courses[code] = {"title": title, "date": when[0], "day": when[2], "time": when[1]}
        if code in ALIASES:
            courses[code]["also"] = ALIASES[code]

        # room map per page (a page with room headers starts a new block)
        current = {}
        for pi in pages:
            if pi["rooms"]:
                current = {col_of(cx, pi["anchors"]): code_ for code_, cx in pi["rooms"]}
                # a header can be centred over several columns (big halls): unlabelled columns inherit the room on their left
                for ci in range(len(pi["anchors"])):
                    if ci not in current and ci - 1 in current:
                        current[ci] = current[ci - 1]
            pi["map"] = dict(current)

        for pi in pages:
            rows = {}
            for w in pi["words"]:
                rows.setdefault(round(w["top"]), []).append(w)
            for _, rws in rows.items():
                rws = sorted(rws, key=lambda w: w["x0"])
                for i, w in enumerate(rws):
                    if not ID_RE.match(w["text"]):
                        continue
                    sec = None
                    grp = None
                    for w2 in rws[i + 1:]:
                        m = SEC_RE.match(w2["text"])
                        if m:
                            grp = m.group(1)
                            sec = m.group(2)
                            break
                    room = pi["map"].get(col_of(w["x0"], pi["anchors"]))
                    if not room:
                        continue
                    # lab sections carry their own course code (CSAI 101 chart -> CSAI 111 students)
                    sc = f"{code.split()[0]} {grp}" if grp else code
                    students.setdefault(w["text"], []).append({
                        "c": code, "sc": sc, "d": when[0], "t": when[1], "r": room, "s": sec or "",
                    })


# ------------------------------------------------- attendance sheets (table layout)
# Some faculties publish attendance sheets instead of grid seating charts. They
# list every ID under a per-room header but use a prose table, so they need their
# own parser. An attendance sheet supersedes any older chart for the same course.
def parse_attendance_sheet(path):
    code = date = time = weekday = None
    rooms = {}
    with pdfplumber.open(path) as pdf:
        for page in pdf.pages:
            text = page.extract_text() or ""
            if code is None:
                m = re.search(r"Course Code\s+([A-Z]{2,8})\s?(\d{3})", text)
                if m:
                    code = f"{m.group(1)} {m.group(2)}"
            if date is None:
                m = re.search(r"Exam Date\s+([A-Za-z]+),\s+(\d{1,2})\s+([A-Za-z]+)\s+(\d{4})", text)
                if m and m.group(4) == "2026" and m.group(3)[:3].upper() in MONTHS:
                    weekday = m.group(1)
                    date = f"2026-{MONTHS[m.group(3)[:3].upper()]:02d}-{int(m.group(2)):02d}"
            if time is None:
                m = re.search(r"Exam Time\s+(\d{2}:\d{2}-\d{2}:\d{2})", text)
                if m:
                    time = m.group(1)
            rm = ATTENDANCE_RE.search(text)
            if rm:
                ids = re.findall(r"(?<!\d)(\d{9})(?!\d)", text)
                rooms.setdefault(rm.group(1), set()).update(ids)
    return code, date, time, weekday, rooms


for f in sorted(glob.glob(os.path.join(folder, "*Attendance*Sheet*.pdf"))):
    acode, adate, atime, aday, arooms = parse_attendance_sheet(f)
    if not (acode and adate and atime and arooms):
        print("skipped attendance sheet:", os.path.basename(f))
        continue
    # drop any rows from an older chart for this course
    for lst in students.values():
        lst[:] = [e for e in lst if e["c"] != acode]
    for aroom, aids in arooms.items():
        for sid in aids:
            students.setdefault(sid, []).append({
                "c": acode, "sc": acode, "d": adate, "t": atime, "r": aroom, "s": "",
            })
    day_idx = [d[:3] for d in DAYS].index(aday[:3].upper()) if aday else None
    courses[acode] = {
        "title": TITLES.get(acode, acode), "date": adate,
        "day": DAYS[day_idx] if day_idx is not None else "",
        "time": atime, "rooms": sorted(arooms),
    }
    print("attendance sheet:", acode, len(set().union(*arooms.values())) if arooms else 0,
          "students", len(arooms), "rooms")


# ------------------------------------------------------- official midterm schedule
def parse_schedule(path):
    """Parse the official schedule table into clean course records."""
    entries = []
    with pdfplumber.open(path) as pdf:
        # Detect column boundaries from the header row on the first page so the
        # parser works for both the portrait and the landscape schedule layouts.
        first_page = pdf.pages[0]
        fw = first_page.extract_words()
        ftop = min(w["top"] for w in fw)
        header = sorted([w for w in fw if abs(w["top"] - ftop) < 3], key=lambda w: w["x0"])
        anchors = []  # (column name, start x)
        i = 0
        while i < len(header):
            w = header[i]
            if w["text"] == "Course" and i + 1 < len(header) and header[i + 1]["text"] in ("Code", "Title"):
                name = "code" if header[i + 1]["text"] == "Code" else "title"
                anchors.append((name, w["x0"]))
                i += 2
                continue
            name_map = {"Day": "day", "Time": "time", "Sections": "sections",
                        "Instructors": "instructors", "Students": "students", "Rooms": "rooms"}
            if w["text"] in name_map:
                anchors.append((name_map[w["text"]], w["x0"]))
            i += 1
        # boundaries: midpoint between consecutive anchor starts
        boundaries = []
        for idx, (name, sx) in enumerate(anchors):
            if idx + 1 < len(anchors):
                nxt = anchors[idx + 1][1]
                cut = (sx + nxt) / 2
            else:
                cut = sx + 1000
            boundaries.append((name, sx, cut))

        def col_for(x):
            chosen = boundaries[0][0]
            for name, sx, cut in boundaries:
                if x >= sx - 4:
                    chosen = name
                else:
                    break
            # ensure monotonic: pick last anchor whose start <= x
            res = boundaries[0][0]
            for name, sx, cut in boundaries:
                if x >= sx - 4:
                    res = name
                else:
                    break
            return res

        for page in pdf.pages:
            # group words into visual rows, then into table columns by x-position
            line_map = defaultdict(list)
            for w in page.extract_words():
                line_map[round(w["top"] / 2) * 2].append(w)
            for top in sorted(line_map):
                cells = defaultdict(list)
                for w in sorted(line_map[top], key=lambda x: x["x0"]):
                    cells[col_for(w["x0"])].append(w["text"])
                rec = {k: " ".join(v).strip() for k, v in cells.items()}
                has_time = bool(rec.get("time")) or bool(re.search(r"\d{2}:\d{2}-\d{2}:\d{2}", rec.get("day", "")))
                if rec.get("day") and has_time:
                    entries.append(rec)
                elif entries and (rec.get("rooms") or rec.get("title") or rec.get("code")):
                    # continuation line (mostly wrapped room lists)
                    for k in ("rooms", "title", "code", "instructors", "students"):
                        if rec.get(k):
                            entries[-1][k] = (entries[-1].get(k, "") + " " + rec[k]).strip()

    catalog = {}
    for rec in entries:
        day_txt = rec.get("day", "")
        time_txt = rec.get("time", "").strip()
        # Some rows lose the space between the date and time ("WED 11th NOV08:30-09:30")
        embedded = re.search(r"(\d{2}:\d{2}-\d{2}:\d{2})", day_txt)
        if embedded:
            time_txt = time_txt or embedded.group(1)
            day_txt = day_txt[:embedded.start()]
        if not re.match(r"^(SAT|SUN|MON|TUE|WED|THU)\b", day_txt):
            continue
        day_info = parse_day(day_txt)
        if not day_info or not re.match(r"^\d{2}:\d{2}-\d{2}:\d{2}$", time_txt):
            continue
        when = (day_info[0], time_txt, day_info[1])
        raw_code = re.sub(r"\s+", " ", rec.get("code", "")).strip()
        # split combined codes: "CSAI 101 / CSAI 111"
        parts = [p.strip() for p in raw_code.split("/") if p.strip()]
        if not parts:
            continue
        def clean_code(c):
            m = re.match(r"^([A-Z]{2,8})\s*(\d{3})", c)
            return f"{m.group(1)} {m.group(2)}" if m else None
        primary = clean_code(parts[0])
        if not primary:
            continue
        also = [c for c in (clean_code(p) for p in parts[1:]) if c and c != primary]
        parsed_title = re.sub(r"\s+", " ", rec.get("title", "")).strip()
        title = TITLES.get(primary) or parsed_title or primary
        rooms = [r.strip() for r in re.split(r",", rec.get("rooms", "")) if re.match(r"^[A-Z0-9]{2,}-[A-Z0-9]\d?$", r.strip())]
        try:
            sections = int(rec.get("sections", "").split()[0])
        except (ValueError, IndexError):
            sections = None
        try:
            headcount = int(rec.get("students", "").split()[0])
        except (ValueError, IndexError):
            headcount = None
        entry = {
            "title": title,
            "date": when[0],
            "day": when[2],
            "time": when[1],
            "rooms": rooms,
        }
        if also:
            entry["also"] = also
        if sections:
            entry["sections"] = sections
        if headcount:
            entry["students"] = headcount
        # prefer the record with a usable room list if a code repeats
        if primary not in catalog or (not catalog[primary].get("rooms") and rooms):
            catalog[primary] = entry

    return catalog


schedule = {}
for _sf in SCHEDULE_FILES:
    if not os.path.exists(_sf):
        continue
    _parsed = parse_schedule(_sf)
    for _code, _entry in _parsed.items():
        if _code not in schedule:
            schedule[_code] = _entry
        else:
            if len(_entry.get("rooms", [])) > len(schedule[_code].get("rooms", [])):
                schedule[_code]["rooms"] = _entry["rooms"]
            if _entry.get("students") and not schedule[_code].get("students"):
                schedule[_code]["students"] = _entry["students"]
            if _entry.get("sections") and not schedule[_code].get("sections"):
                schedule[_code]["sections"] = _entry["sections"]

# charted courses get the schedule's exact date/time/title, but keep chart aliases
for code, c in courses.items():
    if code in schedule:
        c["title"] = schedule[code]["title"]
        c["date"] = schedule[code]["date"]
        c["day"] = schedule[code]["day"]
        c["time"] = schedule[code]["time"]
        if schedule[code].get("also"):
            c["also"] = schedule[code]["also"]
        if schedule[code].get("rooms"):
            c["rooms"] = schedule[code]["rooms"]

# make sure every charted course exists in the full catalogue
for code, c in courses.items():
    if code not in schedule:
        schedule[code] = {
            "title": c["title"], "date": c["date"], "day": c["day"], "time": c["time"],
            "rooms": [],
        }

# charts are the freshest source for room lists and headcounts
rooms_by_course = defaultdict(set)
ids_by_course = defaultdict(set)
for sid, lst in students.items():
    for e in lst:
        if e.get("r"):
            rooms_by_course[e["c"]].add(e["r"])
        ids_by_course[e["c"]].add(sid)
for code, c in schedule.items():
    if rooms_by_course.get(code):
        c["rooms"] = sorted(set(c.get("rooms", [])) | rooms_by_course[code])
    if ids_by_course.get(code):
        c["students"] = len(ids_by_course[code])
    c.setdefault("rooms", [])

for code, c in courses.items():
    if code in schedule:
        c["rooms"] = schedule[code]["rooms"]


# --------------------------------------------------------------- programme guide
# programmes.json in the output directory is the source of truth when it exists,
# so the guide can be edited without touching this script.
PROGRAMME_DEFAULT = {
    "csai": {
        "label": "Computational Science & AI — first year",
        "expected": 6,
        "core": ["MATH 103", "CSAI 101", "CSAI 102", "CSAI 252"],
        "optionGroups": [
            {
                "id": "english",
                "label": "English",
                "hint": "Pick the English level on your registration.",
                "default": "ENGL 003",
                "options": ["ENGL 003", "ENGL 004"],
            },
            {
                "id": "humanities",
                "label": "Ethics or social issues",
                "hint": "Pick the humanity subject on your registration.",
                "default": "SCH 210",
                "options": ["SCH 210", "SCH 263"],
            },
        ],
        "options": ["ENGL 003", "ENGL 004", "SCH 210", "SCH 263"],
    },
    "eng": {
        "label": "Engineering — first year",
        "expected": 6,
        "core": ["MATH 101", "CHEM 103", "PHYS 105", "ENGR 102", "ENGR 121", "CSCI 101"],
        "optionGroups": [
            {
                "id": "english",
                "label": "English",
                "hint": "Pick the English level on your registration.",
                "default": "ENGL 003",
                "options": ["ENGL 003", "ENGL 004"],
            },
            {
                "id": "humanities",
                "label": "Ethics or social issues",
                "hint": "Pick the humanity subject on your registration.",
                "default": "SCH 210",
                "options": ["SCH 210", "SCH 263"],
            },
        ],
        "options": ["ENGL 003", "ENGL 004", "SCH 210", "SCH 263"],
    },
    "csai_upper": {
        "label": "Computational Science & AI — upper year",
        "expected": 6,
        "core": ["CSAI 201", "CSAI 202", "CSAI 205", "DSAI 203", "MATH 105"],
        "optionGroups": [
            {
                "id": "english",
                "label": "English",
                "hint": "Pick the English level on your registration.",
                "default": "ENGL 003",
                "options": ["ENGL 003", "ENGL 004"],
            },
            {
                "id": "humanities",
                "label": "Ethics or social issues",
                "hint": "Pick the humanity subject on your registration.",
                "default": "SCH 210",
                "options": ["SCH 210", "SCH 263"],
            },
        ],
        "options": ["ENGL 003", "ENGL 004", "SCH 210", "SCH 263"],
    },
}

PROGRAMMES = PROGRAMME_DEFAULT
_programmes_path = os.path.join(outdir, "programmes.json")
if os.path.exists(_programmes_path):
    try:
        with open(_programmes_path, encoding="utf-8") as fh:
            loaded = json.load(fh)
        if isinstance(loaded, dict) and loaded:
            PROGRAMMES = loaded
    except (json.JSONDecodeError, OSError):
        pass

# manual enrolments (single-hall courses with no published seating chart)
manual = {}
manual_path = os.path.join(outdir, "manual.json")
if os.path.exists(manual_path):
    try:
        manual = json.load(open(manual_path, encoding="utf-8"))
    except json.JSONDecodeError:
        manual = {}
for sid, extra in manual.items():
    for code in extra:
        c = schedule.get(code) or courses.get(code)
        if not c:
            continue
        room = (c.get("rooms") or [c.get("room") or "—"])[0]
        students.setdefault(sid, []).append({
            "c": code, "sc": code, "d": c["date"], "t": c["time"], "r": room, "s": "",
        })

# de-duplicate and sort
for sid, lst in students.items():
    seen = set()
    clean = []
    for e in lst:
        key = (e["c"], e["d"], e["t"])
        if key in seen:
            continue
        seen.add(key)
        clean.append(e)
    clean.sort(key=lambda e: (e["d"], e["t"]))
    students[sid] = clean

os.makedirs(outdir, exist_ok=True)
with open(os.path.join(outdir, "students.json"), "w", encoding="utf-8") as fh:
    json.dump(students, fh, ensure_ascii=False, separators=(",", ":"))
with open(os.path.join(outdir, "courses.json"), "w", encoding="utf-8") as fh:
    json.dump(courses, fh, ensure_ascii=False, indent=1)
with open(os.path.join(outdir, "catalog.json"), "w", encoding="utf-8") as fh:
    json.dump(schedule, fh, ensure_ascii=False, indent=1, sort_keys=True)
with open(os.path.join(outdir, "programmes.json"), "w", encoding="utf-8") as fh:
    json.dump(PROGRAMMES, fh, ensure_ascii=False, indent=1)
# JS-embedded copy so the site also works when opened straight from disk (file://)
with open(os.path.join(outdir, "students.js"), "w", encoding="utf-8") as fh:
    fh.write("window.STUDENTS=")
    json.dump(students, fh, ensure_ascii=False, separators=(",", ":"))
    fh.write(";\nwindow.COURSES=")
    json.dump(courses, fh, ensure_ascii=False, separators=(",", ":"))
    fh.write(";\nwindow.CATALOG=")
    json.dump(schedule, fh, ensure_ascii=False, separators=(",", ":"))
    fh.write(";\nwindow.PROGRAMMES=")
    json.dump(PROGRAMMES, fh, ensure_ascii=False, separators=(",", ":"))
    fh.write(";\n")

print("students:", len(students), " exams:", sum(len(v) for v in students.values()), " charted courses:", len(courses))
print("catalogue courses:", len(schedule))
print("students.json KB:", round(os.path.getsize(os.path.join(outdir, "students.json")) / 1024, 1))
