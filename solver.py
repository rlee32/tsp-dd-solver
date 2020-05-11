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

def merge_trivial_segments(trivial_segments):
    trivial_map = {}
    kmoves = []
    for s in trivial_segments:
        assert(s['start'] == s['end'])
        i = s['start']
        if i in trivial_map:
            # if a previous trivial added to map already, merge.
            kmoves.append(combine_segments(trivial_map[i], s))
            del trivial_map[i]
        else:
            # otherwise, add trivial to the map, to be retrieved later if i is encountered again.
            trivial_map[i] = s
    # return remaining trivial segments.
    remaining_trivials = [trivial_map[k] for k in trivial_map]
    return kmoves, remaining_trivials

def segments_to_kmoves(segments):
    """segments are all segments that completely describe the difference between 2 local optima."""
    # segments that are cyclic and independent (sequential) k-moves.
    kmoves = [s for s in segments if is_cyclic(s) and is_balanced(s)]
    # trivial segments, segments that are cyclic but not independent k-moves.
    trivials = [s for s in segments if is_cyclic(s) and not is_balanced(s)]
    # segments that are neither independent k-moves nor trivials.
    other = [s for s in segments if not is_cyclic(s)]
    # find trivial segment pairs that can be merged into kmoves, leaving trivials that are part of
    # 2 separate segments.
    kmoves_from_trivials, trivials = merge_trivial_segments(trivials)
    if len(kmoves_from_trivials) > 0:
        print('merged trivials to get {} kmoves!'.format(len(kmoves_from_trivials)))
    kmoves += kmoves_from_trivials
    # TODO: further merge trivials and make kmoves if possible.
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
