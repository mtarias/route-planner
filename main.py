import argparse
import sys

from algorithm import vehicle_assign_calculator
from services import data_export
from services import instance_store


def run_experiment(exp):
    vehicles, packages, matrix_costs = instance_store.load_instance(exp)
    solution_cost, final_solution = vehicle_assign_calculator.calculate(
        vehicles, packages, matrix_costs, verbose=True
    )

    print(f"SOLUTION COST: {solution_cost}")
    for solution in final_solution:
        print(solution)

    data_export.export_results(exp, solution_cost, final_solution)
    return solution_cost, final_solution


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run a vehicle assignment instance.")
    parser.add_argument("experiment", help="Instance folder inside data/, for example exp1")
    args = parser.parse_args()

    try:
        run_experiment(args.experiment)
    except (OSError, ValueError) as error:
        sys.exit(f"Error: {error}")
