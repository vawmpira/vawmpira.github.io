# Midterm Finder — Zewail City University

**Your Fall 2026 midterm schedule, all in one place.**

Enter your 9-digit student ID to instantly find your exams, including their dates, times, rooms, and course details. No digging through PDFs. No manually searching seating charts. Just your schedule.

**[Open Midterm Finder](https://vawmpira.github.io/)**

Midterm Finder is a lightweight, dependency-free web app built using Zewail City's official Fall 2026 midterm schedule and published seating charts.

---

## Features

- **Instant student lookup** — Enter your 9-digit student ID and press Enter to retrieve every exam associated with it.
- **First-year programme defaults** — For 2026 first-year students, the app fills in the two humanities slots (English and ethics/social issues) using the standard programme plan when individual enrolment data is unavailable. These entries are clearly marked as **assumed** and can be corrected directly on the exam card. Corrections are saved for that student ID.
- **Detailed exam cards** — See the course code, course title, section, date, time, room, and a live countdown showing how many days remain until each exam.
- **Exam conflict detection** — Automatically identifies overlapping exams so scheduling issues are easy to spot.
- **Complete exam catalogue** — Browse the official Fall 2026 midterm schedule across all 241 published courses, even without looking up a student ID.
- **Offline support** — The student dataset is embedded in a plain JavaScript file, so the app can run from a local copy without a server or internet connection.

## How it works

1. Open the website.
2. Enter your 9-digit student ID.
3. View your scheduled midterms, organised into individual exam cards.
4. Check each exam's date, time, section, and assigned room.

For first-year students, any course inferred from the standard programme plan is labelled **assumed**. Use the **Change** option to select the course you're actually registered in. You can also use **+ Add another course** to add an exam manually.

---

## Built with

| Component | Technology | Why it was chosen |
|---|---|---|
| Front end | HTML, CSS, and vanilla JavaScript | Lightweight, fast, and dependency-free |
| Data storage | Local JavaScript and JSON files | Works without a backend and avoids cross-origin loading issues |
| Hosting | GitHub Pages | Free static hosting with HTTPS |
| Design | Bricolage Grotesque, custom CSS | A clean, readable interface designed to work well on mobile |

There is no build step, package installation, framework, or external runtime dependency. The app is made to load quickly and remain easy to maintain.

## How the data is collected

The dataset is generated from Zewail City's official midterm seating-chart and attendance-sheet PDFs using a custom Python extraction script.

### Seating-chart extraction

The build script uses **pdfplumber** to extract text from each PDF page while preserving the horizontal position of individual words.

The extraction process works as follows:

1. **Read exam information:** The first page of a seating chart provides the course code, exam date, time, and total student count.
2. **Identify room assignments:** Room codes are extracted from the chart header and mapped to the seating columns beneath them by comparing their horizontal centres.
3. **Assign students to rooms:** Each 9-digit student ID is associated with the room assigned to the column where it appears. Section labels, such as `S04`, are extracted alongside the IDs.
4. **Handle multiple pages:** A repeated room header starts a new seating block. Pages without a new header continue the previous block.
5. **Process attendance sheets:** Some courses use attendance-sheet PDFs instead of traditional seating grids. These have a separate parser that identifies headings such as `Room G011-B (N students)` and assigns the student IDs on that page to the specified room.
6. **Resolve updated records:** An attendance sheet takes priority over an older seating chart when both exist for the same course.
7. **Validate the results:** Extracted student counts are checked against the per-room headcounts printed in the original charts.

### First-year programme data

The file `data/programmes.json` defines each first-year programme, including:

- Required core courses.
- Expected courses.
- Optional course groups.
- Default courses and permitted alternatives.

When this file is available, the build script uses its configuration directly. Otherwise, it falls back to the built-in defaults defined in `tools/build_data.py`.

This allows the app to fill missing first-year humanities enrolments without presenting those assumptions as confirmed registrations.

---

## Regenerating the dataset

To rebuild the dataset from the original PDF files, run:

```bash
python tools/build_data.py ./data "/path/to/folder/containing/the/PDFs"
```

The script generates three files:

| Output | Purpose |
|---|---|
| `data/students.json` | Main student-to-exam dataset |
| `data/courses.json` | Course information, including titles, dates, and times |
| `data/students.js` | JavaScript-embedded copy of the student dataset used by the website |

`students.json` is the source of truth for the generated student data. The JavaScript version allows the site to run locally and on GitHub Pages without requiring a backend.

## Project structure

```text
midterm-lookup/
├── index.html             # Main application page
├── styles.css             # Styling, layout, and animations
├── app.js                 # Lookup logic, rendering, catalogue, and themes
├── data/
│   ├── students.js        # Embedded student dataset
│   ├── students.json      # Main student dataset
│   ├── courses.json       # Course titles and exam details
│   ├── catalog.json       # Complete official Fall 2026 schedule
│   ├── programmes.json    # First-year programme requirements and options
│   └── manual.json        # Enrolments confirmed outside seating charts
└── tools/
    └── build_data.py      # PDF-to-dataset extraction script
```

---

## Data coverage and limitations

The app combines information from two sources: individual student seating charts and the university's official course schedule.

Current dataset coverage:

| Dataset | Coverage |
|---|---:|
| Official courses in the full schedule | 241 |
| Courses with published individual seating charts | 16 |
| Students identified in those seating charts | 1,838 |
| Extracted exam records | 7,219 |

**Important limitations:**

- **Not every course has individual student seating data.** `ENGL 004` has a published seating chart covering 602 students, but `ENGL 003`, `SCH 210`, and `SCH 263` do not currently have individual seating charts available. The app therefore cannot determine which of these courses a particular student is registered in from seating-chart data alone.
- **Humanities courses may be inferred.** For 2026 first-year students, the app uses `ENGL 003` and `SCH 210` as programme defaults when individual enrolment information is unavailable. These entries are marked **assumed**. Students can change them to `ENGL 004` or `SCH 263` where applicable.
- **Engineering first-years are handled differently.** Their six core courses already fill the programme requirements, so no humanities courses are automatically added.
- **Additional courses can be entered manually.** Use **+ Add another course** to include a course that is missing from the available seating-chart data.
- **A missing student ID does not necessarily mean a missing exam.** It means that the ID was not found in the published individual seating charts included in the dataset. Check the entered digits and consult **All exams** for the complete course schedule.

### Room-code format

Room codes follow the university's building, room, and block format.

For example:

`G011-B`

- `G` — Building
- `011` — Room
- `B` — Seating block

Some room labels span multiple seating columns. For example, in `CSAI 102`, room `F005-F` accommodates 264 students across two columns. Unlabelled columns inherit the room assignment of the column to their left.

### Course-specific notes

- `CSAI 252` is extracted from its seating chart, which covers 528 students across rooms `G006-B`, `G011-B`, `G019-B`, and `G025-B`.
- Updated attendance sheets take precedence over older seating charts for the same course.

---

## Built by

**Adam Nael**

- Email: [vawmpira@gmail.com](mailto:vawmpira@gmail.com)
- GitHub: [@vawmpira](https://github.com/vawmpira)

---

**Midterm Finder — Spend less time searching for your exams and more time preparing for them.**
