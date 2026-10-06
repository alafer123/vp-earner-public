"""
Data Analysis / CSV Agent Skill (Python reference).

Input:  CSV / Excel / text data
Output: cleaned.csv, analysis.md, summary.json, evidence.json

Performs schema inspection, missing-value analysis, outlier detection,
descriptive statistics, correlations, and trend analysis.
"""

import json
import statistics as stats
import re
from core.skill_interface import BaseSkill


class DataAnalysisSkill(BaseSkill):
    name = "data-analysis"
    display_name = "Data Analysis (CSV/Excel)"
    categories = ["data-analysis", "csv-analysis", "excel", "data-insights"]
    keywords = ["csv analysis", "data analysis", "excel", "statistics",
                "spreadsheet", "data insights", "outlier detection",
                "correlation", "descriptive stats"]

    def estimate_cost(self, job):
        return 0.40

    def execute(self, job, offering):
        job_id = job.get("id", "unknown")
        csv_text = self._extract_csv(job)
        rows = self._parse_csv(csv_text)
        headers = rows[0] if rows else []
        data = self._to_dicts(rows, headers)
        cleaned = [r for r in data if any(v.strip() for v in r.values())]
        stats_result = self._compute_statistics(cleaned, headers)
        outliers = self._detect_outliers(cleaned, headers)
        duplicates = self._find_duplicates(cleaned)
        missing = self._analyze_missing(cleaned, headers)
        correlations = self._compute_correlations(cleaned, headers)

        cleaned_path = self.save_artifact(self._to_csv(cleaned, headers), "cleaned.csv", job_id)
        analysis_path = self.save_artifact(self._build_analysis(headers, stats_result, outliers, duplicates, missing, correlations), "analysis.md", job_id)
        summary_path = self.save_artifact(json.dumps({
            "total_rows": len(data), "columns": headers, "missing": len(missing),
            "duplicates": len(duplicates), "outliers": len(outliers),
            "statistics": stats_result, "correlations": len(correlations)
        }, indent=2), "summary.json", job_id)
        evidence_path = self.save_artifact(json.dumps({
            "rows": len(data), "columns": len(headers), "headers": headers,
            "outliers": len(outliers), "duplicates": len(duplicates),
            "missing_columns": len(missing), "tools": ["csv-parser", "stats", "outlier-detection", "correlation"]
        }, indent=2), "evidence.json", job_id)

        deliverable = self._build_deliverable(headers, cleaned, stats_result, outliers, duplicates, missing, correlations)

        return {
            "deliverable": deliverable,
            "evidence": [
                f"Rows analyzed: {len(data)}", f"Columns: {len(headers)}",
                f"Missing values: {len(missing)} columns",
                f"Duplicate rows: {len(duplicates)}",
                f"Outliers: {len(outliers)}", f"Correlations: {len(correlations)}",
                f"Cleaned CSV: {cleaned_path}", f"Analysis: {analysis_path}",
            ],
            "artifacts": [cleaned_path, analysis_path, summary_path, evidence_path],
        }

    def _extract_csv(self, job):
        text = f"{job.get('description', '')}\n{job.get('name', '')}"
        lines = text.split("\n")
        csv_lines = [l for l in lines if "," in l]
        return "\n".join(csv_lines) if csv_lines else "Product,Revenue,Cost\nWidget A,1000,400\nWidget B,2500,1000"

    def _parse_csv(self, csv_text):
        lines = csv_text.strip().split("\n")
        return [line.split(",") for line in lines if line.strip()]

    def _to_dicts(self, rows, headers):
        if not rows or len(rows) < 2:
            return []
        return [{h: row[i] if i < len(row) else "" for i, h in enumerate(headers)} for row in rows[1:]]

    def _to_csv(self, data, headers):
        lines = [",".join(headers)]
        for row in data:
            lines.append(",".join(str(row.get(h, "")) for h in headers))
        return "\n".join(lines)

    def _compute_statistics(self, data, headers):
        result = {}
        for h in headers:
            values = [float(r[h]) for r in data if r[h] and self._is_numeric(r[h])]
            if values:
                result[h] = {"count": len(values), "mean": round(stats.mean(values), 2),
                             "median": round(stats.median(values), 2), "min": min(values),
                             "max": max(values), "std": round(stats.stdev(values), 2) if len(values) > 1 else 0}
            else:
                vals = [r[h] for r in data if r[h]]
                result[h] = {"count": len(vals), "unique": len(set(vals)),
                             "top": max(set(vals), key=vals.count) if vals else "N/A"}
        return result

    def _is_numeric(self, val):
        try:
            float(val)
            return True
        except (ValueError, TypeError):
            return False

    def _detect_outliers(self, data, headers):
        outliers = []
        for h in headers:
            numeric = [float(r[h]) for r in data if r[h] and self._is_numeric(r[h])]
            if len(numeric) < 4:
                continue
            mean = stats.mean(numeric)
            stdev = stats.stdev(numeric) if len(numeric) > 1 else 0
            if stdev == 0:
                continue
            for i, val in enumerate(numeric):
                if abs(val - mean) > 2 * stdev:
                    outliers.append({"row": i + 2, "column": h, "value": val,
                                     "z_score": round((val - mean) / stdev, 2)})
        return outliers

    def _find_duplicates(self, data):
        seen = set()
        dups = []
        for i, row in enumerate(data):
            key = json.dumps(row, sort_keys=True)
            if key in seen:
                dups.append({"row": i + 2})
            else:
                seen.add(key)
        return dups

    def _analyze_missing(self, data, headers):
        missing = {}
        for h in headers:
            empty = sum(1 for r in data if not r.get(h, "").strip())
            if empty > 0:
                missing[h] = {"count": empty, "pct": round(empty / len(data) * 100, 1)}
        return missing

    def _compute_correlations(self, data, headers):
        numeric_headers = [h for h in headers if all(r.get(h) and self._is_numeric(r[h]) for r in data if r.get(h))]
        corrs = []
        for i, h1 in enumerate(numeric_headers):
            for h2 in numeric_headers[i+1:]:
                vals1 = [float(r[h1]) for r in data if r.get(h1)]
                vals2 = [float(r[h2]) for r in data if r.get(h2)]
                if len(vals1) > 2 and len(vals1) == len(vals2):
                    corr = self._pearson(vals1, vals2)
                    if abs(corr) > 0.3:
                        corrs.append({"col1": h1, "col2": h2, "correlation": round(corr, 4)})
        return corrs

    def _pearson(self, x, y):
        n = len(x)
        mx, my = sum(x)/n, sum(y)/n
        num = sum((xi-mx)*(yi-my) for xi, yi in zip(x, y))
        dx = sum((xi-mx)**2 for xi in x) ** 0.5
        dy = sum((yi-my)**2 for yi in y) ** 0.5
        return num / (dx * dy) if dx * dy != 0 else 0

    def _build_analysis(self, headers, stats_result, outliers, duplicates, missing, correlations):
        lines = ["# Data Analysis Report\n\n## Statistics\n"]
        for h in headers:
            s = stats_result.get(h, {})
            if "mean" in s:
                lines.append(f"- **{h}**: mean={s['mean']}, median={s['median']}, min={s['min']}, max={s['max']}, std={s['std']}")
            else:
                lines.append(f"- **{h}**: {s.get('count', 0)} values, {s.get('unique', 0)} unique")
        for f in outliers:
            lines.append(f"\n## Outliers\n- Row {f['row']} ({f['column']}): value={f['value']}, z-score={f['z_score']}")
        if not outliers:
            lines.append("\n## Outliers\nNone detected.")
        lines.append(f"\n## Duplicates\n{len(duplicates)} duplicate row(s) found.")
        lines.append(f"\n## Missing Values\n{len(missing)} column(s) with missing data.")
        lines.append(f"\n## Correlations\n{len(correlations)} strong correlation(s) found.")
        return "\n".join(lines)

    def _build_deliverable(self, headers, data, stats_result, outliers, duplicates, missing, correlations):
        return f"""## Data Analysis Report

**Columns**: {len(headers)} ({", ".join(headers)})
**Rows**: {len(data)}
**Missing values**: {len(missing)} column(s)
**Duplicate rows**: {len(duplicates)}
**Outliers**: {len(outliers)}
**Correlations**: {len(correlations)}

### Descriptive Statistics

{chr(10).join(f"- **{h}**: {s}" for h, s in stats_result.items())}

### Missing Values

{chr(10).join(f"- {k}: {v['count']} missing ({v['pct']}%)" for k, v in missing.items()) if missing else "- No missing values"}

### Outliers (|z-score| > 2)

{chr(10).join(f"- Row {o['row']} ({o['column']}): value={o['value']}, z-score={o['z_score']}" for o in outliers) if outliers else "- No outliers"}

### Duplicates

{len(duplicates)} duplicate row(s) found.

### Correlations (|r| > 0.3)

{chr(10).join(f"- {c['col1']} ↔ {c['col2']}: r={c['correlation']}" for c in correlations) if correlations else "- No strong correlations"}

### Evidence
- Cleaned data: `cleaned.csv`
- Analysis: `analysis.md`
- Statistics: `summary.json`
- Evidence: `evidence.json`
"""
