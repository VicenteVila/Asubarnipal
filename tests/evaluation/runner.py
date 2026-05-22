"""Evaluation runner - executes all scenarios and generates reports."""

import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path

REPORTS_DIR = Path(__file__).parent / "reports"
REPORTS_DIR.mkdir(exist_ok=True)


def run_evaluation(levels=None):
    """Run evaluation scenarios and generate report.

    Args:
        levels: list of level numbers to run (default: all 1-4)
    """
    import unittest

    levels = levels or [1, 2, 3, 4]

    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    from tests.evaluation.scenarios import (
        TestLevel1Basic,
        TestLevel2Intermediate,
        TestLevel3Advanced,
        TestLevel4MaxDifficulty,
    )

    test_classes = {
        1: TestLevel1Basic,
        2: TestLevel2Intermediate,
        3: TestLevel3Advanced,
        4: TestLevel4MaxDifficulty,
    }

    for level in levels:
        if level in test_classes:
            tests = loader.loadTestsFromTestCase(test_classes[level])
            suite.addTests(tests)

    runner = unittest.TextTestRunner(verbosity=2)
    start_time = time.time()
    result = runner.run(suite)
    duration = time.time() - start_time

    report = {
        "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "levels_run": levels,
        "total_tests": result.testsRun,
        "passed": result.testsRun - len(result.failures) - len(result.errors) - len(result.skipped),
        "failed": len(result.failures),
        "errors": len(result.errors),
        "skipped": len(result.skipped),
        "duration_seconds": round(duration, 1),
        "failure_list": [
            {
                "test": str(test[0]),
                "error": str(test[1])[:500],
            }
            for test in result.failures
        ],
        "error_list": [
            {
                "test": str(test[0]),
                "error": str(test[1])[:500],
            }
            for test in result.errors
        ],
    }

    effective = report["total_tests"] - report["skipped"]
    report["pass_rate"] = round(
        (report["passed"] / max(1, effective)) * 100, 1
    )

    filename = f"evaluation_{datetime.now().strftime('%Y-%m-%d')}.json"
    report_path = REPORTS_DIR / filename
    report_path.write_text(json.dumps(report, indent=2))

    markdown = generate_markdown_report(report)
    md_path = REPORTS_DIR / f"evaluation_{datetime.now().strftime('%Y-%m-%d')}.md"
    md_path.write_text(markdown)

    print(f"\n{'='*60}")
    print(f"EVALUATION REPORT - {report['date']}")
    print(f"{'='*60}")
    print(f"Tests: {report['total_tests']}")
    print(f"Passed: {report['passed']}")
    print(f"Failed: {report['failed']}")
    print(f"Errors: {report['errors']}")
    print(f"Skipped: {report['skipped']}")
    print(f"Pass rate: {report['pass_rate']}%")
    print(f"Duration: {report['duration_seconds']}s")
    print(f"\nReport saved to: {report_path}")
    print(f"Markdown saved to: {md_path}")

    return report


def generate_markdown_report(report: dict) -> str:
    """Generate markdown report."""
    lines = [
        f"# Evaluacion Asubarnipal - {report['date']}",
        "",
        "## Resumen",
        "",
        "| Metrica | Valor |",
        "|---------|-------|",
        f"| Total tests | {report['total_tests']} |",
        f"| Pasaron | {report['passed']} |",
        f"| Fallaron | {report['failed']} |",
        f"| Errores | {report['errors']} |",
        f"| Saltados | {report['skipped']} |",
        f"| Pass rate | {report['pass_rate']}% |",
        f"| Duracion | {report['duration_seconds']}s |",
        "",
    ]

    if report.get("failure_list"):
        lines.extend([
            "## Fallos",
            "",
            "| Test | Error |",
            "|------|-------|",
        ])
        for f in report["failure_list"]:
            error_short = f["error"][:200].replace("\n", " ")
            lines.append(f"| {f['test']} | {error_short} |")
        lines.append("")

    if report.get("error_list"):
        lines.extend([
            "## Errores",
            "",
            "| Test | Error |",
            "|------|-------|",
        ])
        for e in report["error_list"]:
            error_short = e["error"][:200].replace("\n", " ")
            lines.append(f"| {e['test']} | {error_short} |")
        lines.append("")

    lines.extend([
        "---",
        f"*Generado automaticamente por tests/evaluation/runner.py*",
    ])

    return "\n".join(lines)


if __name__ == "__main__":
    levels_arg = sys.argv[1:] if len(sys.argv) > 1 else None
    if levels_arg:
        levels = [int(l) for l in levels_arg]
    else:
        levels = [1, 2]

    run_evaluation(levels)
