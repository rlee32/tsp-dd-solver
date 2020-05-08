#!/usr/bin/env python3

import reader
import two_opt
import tour_util
import plot_util
import random
from splitter import Splitter

def is_cyclic(segment):
    return segment['start'] == segment['end']

def is_balanced(segment):
    """Balanced means adds == dels."""
    return len(segment['dels']) == len(segment['adds'])

def combine_segments(s1, s2):
    return { 'adds': s1['adds'] + s2['adds'], 'dels': s1['dels'] + s2['dels'] }

def segments_to_kmoves(segments):
    kmoves = []
    trivials = []
    uncategorized = { 'adds': [], 'dels': [] }
    for segment in segments:
        if is_cyclic(segment):
            if is_balanced(segment):
                kmoves.append(segment)
            else:
                trivials.append(segment)
                uncategorized = combine_segments(uncategorized, segment)
        else:
            uncategorized = combine_segments(uncategorized, segment)
    kmoves.append(uncategorized)
    return kmoves

def perturbed_hill_climb(xy, tour):
    tries = 0
    success = 0
    best_length = tour_util.length(xy, tour)
    while True:
        new_tour, new_length = two_opt.optimize(xy, tour_util.double_bridge(tour))
        segments = Splitter(tour, new_tour).get_segments()
        kmoves = segments_to_kmoves(segments)
        print('kmoves: {}'.format(len(kmoves)))
        if new_length < best_length:
            print('found better tour in local optimum {}'.format(tries))
            tour = new_tour
            best_length = new_length
            success += 1
        else:
            print('ignored worse tour in local optimum {}'.format(tries))
        tries += 1
        print('current best: {}, success rate: {}'.format(best_length, success / tries))

if __name__ == "__main__":
    problem_name = 'xqf131'
    xy = reader.read_xy("problems/{}.tsp".format(problem_name))
    tour = tour_util.default(xy)
    tour, improvement = two_opt.optimize(xy, tour)

    """
    tour, improvement = two_opt.optimize(xy, tour)
    new_tour = tour_util.double_bridge(tour)
    new_tour, improvement = two_opt.optimize(xy, new_tour)
    plot_util.plot_difference(xy, tour, new_tour)
    """

    perturbed_hill_climb(xy, tour)
    """
    #random.shuffle(tour)
    for i in range(10):
        new_tour = tour_util.double_bridge(tour)
        plot_util.plot_difference(xy, tour, new_tour)
    """
