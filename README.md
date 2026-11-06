<div align="center">

# Midterm Finder

**Type your student ID. Get every Fall 2026 midterm: date, time, room.**

Zewail City University · 7–14 November 2026

[**Open the site →**](https://vawmpira.github.io/)

`241 courses` · `16 seating charts` · `1,838 students` · `7,219 exam records`

</div>

---

## What it does

| | |
| **Instant lookup** | Fill in nine digits and the schedule opens on its own. No button, no PDFs. |
| **Week ruler** | Your exams on a day × time grid, so the shape of your week is clear at a glance. |
| **Exam cards** | Course, section, date, time, room and a live "in N days" countdown. The next exam is highlighted. |
| **Clash detection** | Overlapping exams are hatched and flagged. |
| **Copy link** | One tap copies a link that opens straight to your schedule (`?id=…`). |
| **Clear** | Wipe the ID and start over without reloading. |
| **All exams** | Browse and filter the full 241-course schedule without an ID. |
| **Mobile first** | Built for a phone in a corridor. The results scroll into view when your ID is complete. |
| **No backend** | Static files only. Works on GitHub Pages or from a local copy. |

## First-year defaults

Some humanities subjects have no per-student chart, so for **2026 first-years** the site fills the two humanities slots from the standard programme plan. These are tagged **assumed**.

- Wrong one? Use the dropdown on the card to switch (for example `ENGL 003` → `ENGL 004`).
- Missing a course entirely? **Add a course** adds it by hand.
- Corrections are saved in your browser for that ID only. Nothing is sent anywhere.

Engineering first-years already have six core courses, so nothing is assumed for them.

## Stack

Plain **HTML, CSS and JavaScript**. No framework, no build step, no runtime dependencies.
Hosted on **GitHub Pages**. Typeset in **Bricolage Grotesque**.

```text
├── index.html          page shell
├── styles.css          layout, greyscale theme, animations
├── app.js              lookup, week ruler, catalogue, copy link
├── data/
│   ├── students.js     student → exams, embedded for offline use
│   ├── students.json   source of truth for the above
│   ├── courses.json    titles, dates, times for charted courses
│   ├── catalog.json    the full official schedule (241 courses)
│   ├── programmes.json first-year plans and options
│   └── manual.json     enrolments confirmed outside the charts
└── tools/build_data.py PDF → dataset extractor
```

## Rebuilding the data

```bash
pip install pdfplumber
python tools/build_data.py ./data "/path/to/folder/with/the/PDFs"
```

Writes `students.json`, `students.js`, `courses.json` and `catalog.json`. Put `Exam_Schedule.pdf` and the per-course seating charts (`MATH_101.pdf`, …) in the same folder.

<details>
<summary><b>How the extraction works</b></summary>

<br>

1. **Header.** Page one gives the course, date, time and total headcount.
2. **Rooms.** Room codes are read from the header and matched to seating columns by horizontal position.
3. **Students.** Each 9-digit ID takes the room of the column it sits in, plus its section label (`S04`).
4. **Pages.** A repeated room header starts a new block; pages without one continue the last.
5. **Wide rooms.** A header can be centred over several columns. Unlabelled columns inherit the room on their left (`CSAI 102`: `F005-F` holds 264 students across two).
6. **Attendance sheets.** A separate parser reads `Room G011-B (N students)` pages and overrides an older chart for the same course.
7. **Validation.** Every course's extracted count is checked against the headcount printed on its chart. All 16 currently match.

Course codes come from the file name, because a header can lose its first letter (`SAI 202`).

</details>

## Limits worth knowing

- Only **16 of 241** courses publish per-student charts. `ENGL 003`, `SCH 210` and `SCH 263` do not, so those are assumed or added by hand.
- **ID not found** means it isn't on any published chart, not that you have no exams. Check the digits and use **All exams**.
- Room codes read **building · room · block**: `G011-B` is building G, room 011, block B.

---

<div align="center">

Built by **[Adam Nael](https://github.com/vawmpira)** · [vawmpira@gmail.com](mailto:vawmpira@gmail.com)

*Less time searching for your exams, more time preparing for them.*

</div>
