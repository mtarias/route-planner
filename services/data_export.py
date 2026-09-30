import json
from pathlib import Path

RESULTS_ROOT = Path(__file__).resolve().parent.parent / "results"


def export_results(exp, solution_cost, final_solution):
    RESULTS_ROOT.mkdir(exist_ok=True)
    (RESULTS_ROOT / f"results_{exp}.json").write_text(
        json.dumps(
            {"experiment": exp, "solution_cost": solution_cost, "assignments": final_solution},
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
