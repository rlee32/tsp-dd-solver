#!/usr/bin/env python3

import reader
import two_opt
import basic
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
    otherwise, return None, meaning new segment has been placed in segment_map.
    """
    i = trivial_segment['start']
    assert(i == trivial_segment['end'])
    if i not in segment_map:
        # trivial_segment is not connected to any other segments, and should be merged with another
        # trivial segment.
        return trivial_segment
    total_adds = sum([len(x['adds']) for x in segment_map[i]]) + len(trivial_segment['adds'])
    segments = segment_map[i]
    assert(len(segments) == 2)
    new_segment = combine_segments(trivial_segment, combine_segments(segments[0], segments[1]))
    new_segment['start'] = get_other(segments[0], i)
    new_segment['end'] = get_other(segments[1], i)
    assert(len(new_segment['adds']) == total_adds)
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
    total_adds = sum([len(x['adds']) for x in segments]) + sum([len(x['adds']) for x in trivials])
    segment_map = make_segment_map(segments)
    new_trivials = []
    kmoves = []
    for t in trivials:
        merged_segment = remove_trivial(segment_map, t)
        if not merged_segment:
            # non-trivial segment was added to segment_map.
            continue
        assert(is_cyclic(merged_segment))
        if is_balanced(merged_segment):
            kmoves.append(merged_segment)
        else:
            new_trivials.append(merged_segment)
    assert(len(new_trivials) % 2 == 0)
    # merge trivials that met at a common point.
    if new_trivials:
        kmoves_from_trivials, remaining_segments = merge_trivial_segments(new_trivials)
        assert(not remaining_segments)
        kmoves += kmoves_from_trivials
    # finally, merge all remaining segments that were not split into one kmove.
    # TODO: there might be a way to efficiently split these segments into further independent kmoves.
    last_kmove = {'adds': set(), 'dels': set()}
    for i in segment_map:
        for s in segment_map[i]:
            last_kmove['adds'].update(s['adds'])
            last_kmove['dels'].update(s['dels'])
    last_kmove['adds'] = list(last_kmove['adds'])
    last_kmove['dels'] = list(last_kmove['dels'])
    kmoves.append(last_kmove)
    kmove_adds = sum([len(x['adds']) for x in kmoves])
    assert(total_adds == kmove_adds)
    return kmoves

def kmove_gain(xy, segment):
    gain = sum([basic.edge_cost(xy, edge) for edge in segment['dels']])
    loss = sum([basic.edge_cost(xy, edge) for edge in segment['adds']])
    return gain - loss

def make_adjacency_map(tour):
    adjacency = {}
    n = len(tour)
    for si in range(n):
        i = tour[si]
        adjacency[i] = [tour[si - 1], tour[(si + 1) % n]]
    return adjacency

def perform_kmove(adjacency_map, kmove):
    for d in kmove['dels']:
        adjacency_map[d[0]] = [x for x in adjacency_map[d[0]] if d[1] != x]
        adjacency_map[d[1]] = [x for x in adjacency_map[d[1]] if d[0] != x]
    for a in kmove['adds']:
        adjacency_map[a[0]].append(a[1])
        adjacency_map[a[1]].append(a[0])
    for i in adjacency_map:
        assert(len(adjacency_map[i]) == 2)

def walk_adjacency_map(adjacency_map):
    start = 0
    i = adjacency_map[start][0]
    prev = start
    traversed = 1
    while i != start:
        if adjacency_map[i][0] == prev:
            prev = i
            i = adjacency_map[i][1]
        else:
            prev = i
            i = adjacency_map[i][0]
        traversed += 1
    return traversed

def is_feasible(tour, kmove):
    adj = make_adjacency_map(tour)
    perform_kmove(adj, kmove)
    traversed = walk_adjacency_map(adj)
    return traversed == len(tour)

def combine_segment_array(segments):
    combined = segments[0]
    for s in segments[1:]:
        combined = combine_segments(combined, s)
    return combined

def segments_to_kmoves(xy, segments, tour):
    """segments are all segments that completely describe the difference between 2 local optima.
    Returns beneficial kmoves."""
    total_adds = sum([len(x['adds']) for x in segments])
    total_dels = sum([len(x['dels']) for x in segments])
    assert(total_adds == total_dels)
    # segments that are cyclic and independent (sequential) k-moves.
    kmoves = [s for s in segments if is_cyclic(s) and is_balanced(s)]
    # trivial segments, segments that are cyclic but not independent k-moves.
    trivials = [s for s in segments if is_cyclic(s) and not is_balanced(s)]
    # segments that are neither independent k-moves nor trivials.
    other = [s for s in segments if not is_cyclic(s)]
    # find trivial segment pairs that can be merged into kmoves, leaving trivials that are part of
    # 2 separate segments.
    assert(len(segments) == len(kmoves) + len(trivials) + len(other))
    total_trivial_adds = sum([len(x['adds']) for x in trivials])
    kmoves_from_trivials, trivials = merge_trivial_segments(trivials)
    assert(total_trivial_adds == sum([len(x['adds']) for x in kmoves_from_trivials]) + sum([len(x['adds']) for x in trivials]))
    kmoves += kmoves_from_trivials
    # Consume all trivials to produce remaining kmoves.
    remaining_kmoves = consume_all_trivials(other, trivials)
    kmoves += remaining_kmoves
    #print('    total independent kmoves found in local optima diff: {}'.format(len(kmoves)))
    non_feasible_kmoves = [] # tuple (gain, kmove)
    beneficial_kmoves = []
    for k in kmoves:
        total_adds -= len(k['adds'])
        total_dels -= len(k['dels'])
        feasible = is_feasible(tour, k)
        gain = kmove_gain(xy, k)
        if feasible:
            if gain > 0:
                print('        {}-opt move with gain {}'.format(len(k['dels']), gain))
                beneficial_kmoves.append(k)
        else:
            non_feasible_kmoves.append((gain, k))
    assert(total_adds == 0)
    assert(total_dels == 0)
    if non_feasible_kmoves:
        gain = sum([x[0] for x in non_feasible_kmoves])
        if gain > 0:
            kmove_from_nonfeasible = combine_segment_array([x[1] for x in non_feasible_kmoves])
            # need to check feasibility. It might make sense that independent k-moves should be independent from all non-feasible moves,
            # but consider this example: a non-sequential 4-opt move consisting of 2 2-opt moves, one of which creates 2 cycles, and
            # the other joining the 2 cycles. The joining move alone can either create 2 cycles or not (an independent k-move) in order
            # for the 4-opt move to be feasible. This means the first 2-opt move will be non-feasible alone, while the 2nd 2-opt move
            # can either be non-feasible or feasible, meaning the 4-opt move can have either only 1 non-feasible moves or 2.
            if is_feasible(tour, kmove_from_nonfeasible):
                print('        total gain for {} non-feasible moves: {}'.format(len(non_feasible_kmoves), gain))
                beneficial_kmoves.append(kmove_from_nonfeasible)
    return beneficial_kmoves

def perturbed_hill_climb(xy, tour):
    tries = 0
    success = 0
    best_length = tour_util.length(xy, tour)
    while True:
        new_tour, new_length = two_opt.optimize(xy, tour_util.double_bridge(tour))
        segments = Splitter(tour, new_tour).get_segments()
        kmoves = segments_to_kmoves(xy, segments, tour)
        if new_length < best_length:
            print('found better tour in local optimum {}'.format(tries))
            tour = new_tour
            best_length = new_length
            success += 1
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
