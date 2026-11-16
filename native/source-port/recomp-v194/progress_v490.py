# SPDX-License-Identifier: GPL-2.0-or-later
"""Aggregate AOT inventory; percentages refer to explicit offline denominators."""
from decimal import Decimal, ROUND_DOWN

MILESTONES = (10, 25, 50, 75, 90, 100)


def ratio(done, total):
    if type(done) is not int or type(total) is not int or not 0 <= done <= total or not total:
        raise ValueError('invalid coverage counts')
    p=(Decimal(done)*100/total).quantize(Decimal('0.01'), rounding=ROUND_DOWN)
    return dict(done=done, total=total, percent=str(p),
                reached=[m for m in MILESTONES if done*100>=total*m],
                next=next((m for m in MILESTONES if done*100<total*m),None))


def inventory(roots, families, constructors, verified_prefix=None):
    roots=set(roots)
    covered=set()
    counts={}
    for name,rows in sorted(families.items()):
        ids=list(rows)
        unique=set(ids)
        if len(unique)!=len(ids) or unique & covered or not unique<=roots:
            raise ValueError('duplicate, overlapping or unknown generated ID')
        covered.update(unique)
        counts[name]=len(unique)
    ctors=list(constructors)
    if not ctors or not set(ctors)<=roots:
        raise ValueError('invalid constructor sequence')
    return dict(format='native-aot-inventory-v490', generated_by_family=counts,
                metadata_start_generation=ratio(len(covered),len(roots)),
                constructor_slots_generation=ratio(sum(a in covered for a in ctors),len(ctors)),
                ordered_runtime_prefix=None if verified_prefix is None else ratio(verified_prefix,len(ctors)),
                linked_full_game_coverage=None, gameplay_coverage=None)


def shared_bodies(rows):
    """All generated expressions are pure RAX/flags transforms, no address reads."""
    bodies={}
    ids={}
    for a,_,lines in rows:
        body=tuple(lines)
        if a in ids:
            raise ValueError('duplicate arithmetic ID')
        if body not in bodies:
            bodies[body]=len(bodies)
        ids[a]=bodies[body]
    return bodies,ids
