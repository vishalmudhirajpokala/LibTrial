# 🧪 LibTrial — Evidence-Backed Investigation Report
*Generated on: 2026-10-12 07:02:54 UTC*

---

## 1. Inspected Target Project Profile
- **Project Name:** `fast-analytics`
- **Target Python Version:** `>=3.11`
- **Detected Frameworks:** `fastapi`, `pydantic`
- **Configuration Files Located:** `pyproject.toml`
- **Total Python Files Scanned:** 1

### Declared Project Dependencies
- `fastapi>=0.100.0`
- `pydantic>=2.0.0`
- `requests>=2.28.0`
- `urllib3==1.26.15`

## 2. Developer Capability Requirement
> "High-performance CSV and Parquet reader with lazy evaluation"

## 3. Candidate Library Comparison & Registry Verification
All package proposals originate as **Gemma 4 hypotheses** and are checked against the official **PyPI JSON API**.

| Candidate | Registry Status | Latest Version | Requires-Python | License | Compatibility Finding |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **`polars`** | [Found on PyPI](https://pypi.org/project/polars/) | `2.0.0` | `>=3.10` | `Copyright (c) 2025 Ritchie Vink
        Copyright (c) 2024 (Some portions) NVIDIA CORPORATION & AFFILIATES. All rights reserved.
        
        Permission is hereby granted, free of charge, to any person obtaining a copy
        of this software and associated documentation files (the "Software"), to deal
        in the Software without restriction, including without limitation the rights
        to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
        copies of the Software, and to permit persons to whom the Software is
        furnished to do so, subject to the following conditions:
        
        The above copyright notice and this permission notice shall be included in all
        copies or substantial portions of the Software.
        
        THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
        IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
        FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
        AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
        LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
        OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
        SOFTWARE.` | 🟢 COMPATIBLE WITH AVAILABLE EVIDENCE |
| **`duckdb`** | [Found on PyPI](https://pypi.org/project/duckdb/) | `1.5.6` | `>=3.10.0` | `MIT License` | 🟢 COMPATIBLE WITH AVAILABLE EVIDENCE |

### Detailed Candidate Evidence
#### 1. `polars`
- **Expected Import Name:** `polars` *(Hypothesis)*
- **Proposed Capability:** High-throughput DataFrame processing and lazy evaluation *(Hypothesis)*
- **Project Fit Rationale:** Efficient multithreaded Parquet reader with low memory overhead *(Hypothesis)*
- **Evidence Required:** Check Python 3.11 wheel availability and direct dependencies *(Hypothesis)*
- **PyPI Registry URL:** https://pypi.org/project/polars/ *(PyPI API)*
- **Direct Dependencies Declared:** 31 packages *(PyPI API)*
- **Python Compatibility Details:** Python versions overlap (3.11, 3.12, 3.13, 3.14). Project '>=3.11' compatible with Candidate '>=3.10'.
- **Direct Dependency Collisions:** None detected against declared project pins.

#### 2. `duckdb`
- **Expected Import Name:** `duckdb` *(Hypothesis)*
- **Proposed Capability:** In-process analytical SQL database *(Hypothesis)*
- **Project Fit Rationale:** Zero-copy querying directly over CSV and Parquet files *(Hypothesis)*
- **Evidence Required:** Verify PyPI existence and wheel binary distributions *(Hypothesis)*
- **PyPI Registry URL:** https://pypi.org/project/duckdb/ *(PyPI API)*
- **Direct Dependencies Declared:** 6 packages *(PyPI API)*
- **Python Compatibility Details:** Python versions overlap (3.11, 3.12, 3.13, 3.14). Project '>=3.11' compatible with Candidate '>=3.10.0'.
- **Direct Dependency Collisions:** None detected against declared project pins.

## 4. Isolated Integration Trial
- **Selected Candidate:** `polars`
- **Trial Outcome:** **`PASS`**
- **User Consent Granted:** Yes
- **Docker Boundary Used:** Disposable Docker Container
- **Exit Code:** `0`
- **Execution Runtime:** `1.18s`

### Trial Notes
- Probe completed with exit code 0.

### Proposed Integration Probe Script
```python
import polars as pl

df = pl.DataFrame({"id": [1, 2], "val": [10.5, 20.0]})
print("PROBE_OK: Polars initialized successfully in container")
```

### Container Standard Output
```text
PROBE_OK: Polars initialized successfully in container
```

## 5. Trust, Scope, and Safety Disclaimers
1. **Hypothesis vs. Fact:** AI-generated recommendations are hypotheses. Evidence in this brief is derived solely from official PyPI registry responses, declared project files, and isolated container execution.
2. **No Guarantee of Production Readiness:** A `PASS` outcome in a minimal integration probe confirms isolated syntax and basic initialization only. It does not establish full application compatibility, performance characteristics, or freedom from regressions.
3. **Scope of Dependency Analysis:** LibTrial evaluates direct version constraints declared in project configuration files. Transitive dependency resolution, C-extension build dependencies, and system-level shared libraries are unverified.
4. **Host Environment Protection:** Host environments remain untouched; candidate packages are never installed or run on the host system.
