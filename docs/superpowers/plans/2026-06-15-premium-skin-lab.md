# Premium Skin Lab Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Create an isolated evidence-backed TMUF/TMNF StadiumCar premium skin generator workspace.

**Architecture:** Keep source evidence under `resources/`, code under `src/`, recipes under `recipes/`, and generated artifacts under `out/`. The first implementation slice creates the evidence ledger and a stock Diffuse-only calibration package.

**Tech Stack:** Python 3, Pillow, NumPy, SciPy, stdlib unittest, local DDS encoder.

---

### Task 1: Workspace And Evidence Locker

**Files:**

- Create: `resources/authoritative/`
- Create: `resources/reference_only/`
- Create: `resources/experimental/`
- Create: `src/evidence/build_manifest.py`
- Test: `tests/test_evidence_and_calibration.py`

- [x] **Step 1: Create folder structure**

Run:

```bash
mkdir -p /Users/ydeshwari/Documents/TMUF_PremiumSkinLab/{docs,resources/authoritative,resources/reference_only,resources/experimental,src,recipes,out,tests}
```

- [x] **Step 2: Copy approved evidence resources**

Copy only the stock references, downloaded reference packs, GBuffer/labels, and experimental donor tools.

- [x] **Step 3: Write manifest test**

The test must require `resources/evidence_manifest.json` and verify labels for stock PSD, GBuffer, V2 zip, and CH_2026 donor zip.

- [x] **Step 4: Verify test fails**

Run:

```bash
python3 -m unittest discover -s tests
```

Expected: failure because manifest does not exist.

- [x] **Step 5: Implement manifest builder**

Create `src/evidence/build_manifest.py` to scan copied resources and write SHA256, size, metadata, evidence label, safe use, and limits.

- [x] **Step 6: Generate manifest**

Run:

```bash
python3 -m src.evidence.build_manifest
```

Expected: `resources/evidence_manifest.json` is written.

### Task 2: Stock Diffuse Calibration

**Files:**

- Create: `src/stock_diffuse/calibration.py`
- Create: `recipes/stock_calibration.py`
- Test: `tests/test_evidence_and_calibration.py`

- [x] **Step 1: Write calibration artifact test**

The test must require `out/skins/calibration_stock_diffuse.zip` with only
`Diffuse.dds` and `Icon.dds`.

- [x] **Step 2: Verify test fails**

Run:

```bash
python3 -m unittest discover -s tests
```

Expected: failure because calibration output does not exist.

- [x] **Step 3: Implement calibration generator**

Use copied GBuffer, label map, and AO inputs to paint red nose, blue tail, green
left, yellow right, white roof, dark floor, magenta mudguards, and cyan
centerline.

- [x] **Step 4: Generate calibration package**

Run:

```bash
python3 recipes/stock_calibration.py
```

Expected: calibration zip, atlas preview, projected preview, and JSON report.

### Task 3: Documentation

**Files:**

- Create: `README.md`
- Create: `docs/evidence_rules.md`
- Create: `docs/master_plan.md`
- Create: `docs/resource_usage.md`
- Create: `docs/validation_checklist.md`

- [x] **Step 1: Document evidence labels**

Define `proven`, `reference_only`, `experimental`, and `rejected`.

- [x] **Step 2: Document master plan**

Record stock Diffuse lane, CH_2026 full-car lane, no-mudguard lane, and proof
gates.

- [x] **Step 3: Document validation checklist**

Record package, evidence, visual, and TMUF smoke checks.

### Task 4: Verification

**Files:**

- Verify: all generated outputs

- [ ] **Step 1: Run unit tests**

Run:

```bash
python3 -m unittest discover -s tests
```

Expected: `Ran 2 tests` and `OK`.

- [ ] **Step 2: Compile Python**

Run:

```bash
python3 -m py_compile src/evidence/build_manifest.py src/stock_diffuse/calibration.py recipes/stock_calibration.py
```

Expected: exit code 0.

- [ ] **Step 3: Inspect generated zip**

Run:

```bash
unzip -l out/skins/calibration_stock_diffuse.zip
```

Expected: only `Diffuse.dds` and `Icon.dds`.

