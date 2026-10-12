# LibTrial

> **Gemma 4-powered evaluation of open-source Python libraries for existing projects.**

LibTrial helps developers identify the right open-source library for a specific capability requirement and verifies compatibility against their local project environment before adoption.

---

## ⚡ Core Philosophy
- **Evidence-Backed**: Recommendations are verified against real PyPI registry metadata, not hallucinated LLM claims.
- **Safe Sandboxing**: Candidate integration trials run inside isolated, disposable Docker containers—never executing arbitrary code on the host machine.
- **Transparent Status**: Any compatibility detail that cannot be verified deterministically is labeled `Unknown`.

---

## 📐 Workflow Architecture
The application executes five connected stages in strict order:

```text
PROJECT  ───>  DISCOVERY  ───>  VERIFICATION  ───>  TRIAL  ───>  REPORT
```

1. **PROJECT**: Inspects the target repository profile (Python target, dependencies, frameworks, config files, source excerpts).
2. **DISCOVERY**: Gemma 4 generates up to three candidate package hypotheses for the plain-language requirement.
3. **VERIFICATION**: Fetches official PyPI registry metadata and checks Python version and direct dependency collisions.
4. **TRIAL**: Selects one candidate, generates a minimal integration probe, validates AST safety, and executes in a disposable container.
5. **REPORT**: Exports a comprehensive, auditable Markdown investigation brief (`libtrial_report.md`).

---

## 🚀 Quickstart

### 1. Installation
Clone the repository and install in editable mode:
```bash
pip install -e .
```

### 2. Configure Environment
Copy `.env.example` to `.env` and provide your Google Gemini API key:
```bash
cp .env.example .env
```
Edit `.env`:
```ini
GEMINI_API_KEY="your_actual_key_here"
GEMMA_MODEL="gemma-4-26b-a4b-it"
```

### 3. Launch Application
Start the Streamlit interface:
```bash
streamlit run app.py
```

### 4. Run Test Suite
```bash
pytest
```

---

## 🎮 Hackathon Demonstration Script

1. **Start the app**:
   ```bash
   streamlit run app.py
   ```
2. **Load the Sample Project**:
   - In Stage 1, click **📁 Use Sample Project Fixture** (loads `examples/sample_project`).
   - Click **🔎 Inspect Repository Profile** to view the detected profile (Target: `>=3.11`, Framework: `fastapi`, Pins: `urllib3==1.26.15`).
3. **Discover Candidates**:
   - In Stage 2, click **⚡ Load Example Requirement** (*"High-performance CSV and Parquet reader with lazy evaluation"*).
   - Click **🤖 Generate Candidate Hypotheses & Verify**.
4. **Review Verification & Compatibility**:
   - Inspect the candidate comparison cards in Stage 3.
   - Note the live PyPI version badges, license disclosures, and compatibility findings.
5. **Run Integration Trial**:
   - In Stage 4, select `polars` and click **⚙️ Generate Minimal Integration Probe**.
   - Review the generated probe and observe the **🛡️ AST Safety Check Passed** badge.
   - Check the authorization box and click **🚀 Run Isolated Trial for polars**.
   - Observe the container telemetry or the Docker guardrail report if Docker is inactive.
6. **Export Investigation Report**:
   - In Stage 5, click **💾 Download Markdown Report** to export the brief.

---

## 📄 License
Distributed under the MIT License. See [LICENSE](LICENSE) for details.
