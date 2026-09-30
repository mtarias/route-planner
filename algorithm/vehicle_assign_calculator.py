# Algorithm to assign packages to vehicles using a greedy strategy
# Input: Dict<Vehicle> vehicles, Array<Package> packages, Dict<Cost> matrix_costs
# Output: Integer solution_cost, Array<String> final_solution
def calculate(vehicles, packages, matrix_costs, verbose=False):

    # Init variables
    solution_cost = 0
    final_solution = []

    # Sort packages by weight (desc)
    packages = sorted(packages, key=lambda x: x.weight, reverse=True)

    # Init algorithm
    for package in packages:

        # Get biggest package
        package_name = package.name
        package_costs = matrix_costs[package_name]

        # Sort costs (asc) and vehicle free space (desc)
        sorted_costs = sorted(package_costs, key=lambda x: (x.cost, -(x.vehicle.capacity-x.vehicle.occupied_space)/x.vehicle.capacity))
        i = len(package_costs)
        a = 0

        while i > 0:
            # Get min cost of sorted_costs for package
            min_cost = sorted_costs[a].cost

            # Get vehicle capacity
            vehicle_name = sorted_costs[a].vehicle.name
            vehicle = vehicles[vehicle_name]
            free_space = vehicle.capacity - vehicle.occupied_space

            # Check vehicle capacity
            # if is lower, then add to solution and change vehicle capacity
            if package.weight <= free_space and package.incompatibles not in vehicle.packages:
                
                # Add to solution
                final_solution.append('Package: '+ package.name + ', Vehicle: '+ vehicle_name + ', Cost: '+str(min_cost))
                vehicle.packages.append(package.name)

                # Update vehicle space
                vehicle.occupied_space += package.weight
                solution_cost += min_cost
                i = 0
                if verbose:
                    print('PACKAGE '+str(package.name)+' ASSIGNED TO '+str(vehicle.name)+', COST: '+str(min_cost)+' , FREE SPACE: '+str(vehicle.capacity-vehicle.occupied_space))
            
            # Else, go to the next cost of sorted_costs
            else:
                if verbose:
                    print('PACKAGE '+str(package.name)+' CANNOT BE ASSIGNED TO '+str(vehicle.name)+', WEIGHT: '+str(package.weight)+' , FREE SPACE: '+str(vehicle.capacity-vehicle.occupied_space))
                i -= 1
                a += 1
    
    return solution_cost, final_solution

    