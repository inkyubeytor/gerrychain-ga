from functools import partial
from time import time

from gerrychain import GeographicPartition, Graph, MarkovChain, accept, \
    constraints, updaters
from gerrychain.proposals import recom
import numpy as np

import ga_psc_districts


STEPS = 100000
COUNTIES = 159


graph = Graph.from_file("Counties_Georgia.zip", ignore_errors=True)

# Configure our updaters (everything we want to compute
# for each plan in the ensemble).

# Population updater, for computing how close to equality the district
# populations are. "totpop10" is the population column from our shapefile.
my_updaters = {"population": updaters.Tally("totpop10", alias="population")}

# GeographicPartition comes with built-in ``area`` and ``perimeter`` updaters.
initial_partition = GeographicPartition(graph,
                                        assignment=ga_psc_districts.assignment,
                                        updaters=my_updaters)

# The recom proposal needs to know the ideal population for the districts so
# that we can improve speed by bailing early on unbalanced partitions.

ideal_population = sum(initial_partition["population"].values()) / len(
    initial_partition)

# We use functools.partial to bind the extra parameters
# (pop_col, pop_target, epsilon, node_repeats)
# of the recom proposal.
proposal = partial(recom,
                   pop_col="totpop10",
                   pop_target=ideal_population,
                   epsilon=0.05,
                   node_repeats=2
                   )

# Configure the MarkovChain.

chain = MarkovChain(
    proposal=proposal,
    constraints=[
        # District populations must stay within 5% of equality
        constraints.within_percent_of_ideal_population(initial_partition, 0.05)
    ],
    accept=accept.always_accept,
    initial_state=initial_partition,
    total_steps=STEPS
)

maps = np.zeros((STEPS, COUNTIES))

for i, partition in enumerate(chain):
    data = sorted(list(partition.assignment.items()))
    keys = np.array([i for i, _ in data])
    vals = np.array([j for _, j in data])

    # duplicate prevention
    first = np.zeros(5)
    pos = []
    for val in range(1, 6):
        p = np.where(vals == val)[0]
        pos.append(p)
        first[val - 1] = p[0]
    new_nums = np.argsort(first)
    for val, num in enumerate(new_nums):
        vals[pos[num]] = val + 1

    maps[i, keys] = vals

maps = np.unique(maps, axis=0)

print(maps.shape)

np.save(f"unique_ga_maps_{STEPS}_{time()}.npy", maps)
