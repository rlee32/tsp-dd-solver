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

def get_other(segment, i):
    if segment['start'] == i:
        return segment['end']
    else:
        return segment['start']

def has_point(point, segment):
    return point == segment['start'] or point == segment['end']

def remove_segments(segment_map, start_point, end_point):
    segment_map[start_point] = [s for s in segment_map[start_point] if not has_point(start_point, s) or not has_point(end_point, s)]
    if len(segment_map[start_point]) == 0:
        del segment_map[start_point]
    segment_map[end_point] = [s for s in segment_map[end_point] if not has_point(start_point, s) or not has_point(end_point, s)]
    if len(segment_map[end_point]) == 0:
        del segment_map[end_point]

def add_segment(segment_map, new_segment):
    i = new_segment['start']
    j = new_segment['end']
    assert(i != j) # make sure this is not a cyclic segment.
    # if this add_segment is used to replace a just-removed segment, then the number of existing
    # segments should be equal to 1 or 3.
    segment_map[i].append(new_segment)
    segment_map[j].append(new_segment)

def remove_trivial(segment_map, trivial_segment):
    """Removes trivial junction from the segment map, merging the segments at trivial junction.
    segment_map does not contain trivial segments.
    May be called recursively in case merging results in another trivial segment.
    Returns independent k-move if result of merge, or trivial segment if no other merges possible
    (this means another trivial should be merged).
    otherwise, return None.
    """
    i = trivial_segment['start']
    assert(i == trivial_segment['end'])
    if i not in segment_map:
        # trivial_segment is not connected to any other segments, and should be merged with another
        # trivial segment.
        return trivial_segment
    segments = segment_map[i]
    assert(len(segments) == 2)
    new_segment = combine_segments(trivial_segment, combine_segments(segments[0], segments[1]))
    new_segment['start'] = get_other(segments[0], i)
    new_segment['end'] = get_other(segments[1], i)
    remove_segments(segment_map, i, new_segment['start'])
    # new_segment could be an independent k-move.
    if is_cyclic(new_segment):
        if is_balanced(new_segment):
            return new_segment
        else:
            return remove_trivial(segment_map, new_segment)
    else:
        remove_segments(segment_map, i, new_segment['end'])
        add_segment(segment_map, new_segment)

def make_segment_map(segments):
    segment_map = {}
    for s in segments:
        i = s['start']
        j = s['end']
        assert(i != j)
        if i not in segment_map:
            segment_map[i] = [s]
        else:
            segment_map[i].append(s)
        if j not in segment_map:
            segment_map[j] = [s]
        else:
            segment_map[j].append(s)
    return segment_map

def consume_all_trivials(segments, trivials):
    """segments are non-trivial, acyclic segments."""
    segment_map = make_segment_map(segments)
    new_trivials = []
    kmoves = []
    for t in trivials:
        merged_segment = remove_trivial(segment_map, t)
        if not merged_segment:
            continue
        assert(is_cyclic(merged_segment))
        if is_balanced(merged_segment):
            kmoves.append(merged_segment)
        else:
            new_trivials.append(merged_segment)
    assert(len(new_trivials) % 2 == 0)
    if new_trivials:
        kmoves_from_trivials, remaining_segments = merge_trivial_segments(new_trivials)
        assert(not remaining_segments)
        kmoves += kmoves_from_trivials
    if len(kmoves) > 0:
        print('    got {} more kmoves from consume_all_trivials.'.format(len(kmoves)))
    return kmoves

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
    # Consume all trivials to produce remaining kmoves.
    remaining_kmoves = consume_all_trivials(other, trivials)
    kmoves += remaining_kmoves
    print('    total independent kmoves found in local optima diff: {}'.format(len(kmoves)))
    for k in kmoves:
        print('        {}'.format(len(k['dels'])))
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
