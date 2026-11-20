# SPDX-License-Identifier: GPL-2.0-or-later
"""Read and apply Bloodborne EMEVD argument substitutions without executing opcodes."""
from collections import defaultdict
from struct import Struct

from audit_emevd_v717 import EVENT, HEAD, INSN, audit, span

PARAMETER = Struct('<3q2i')


def plans(raw):
    """Return event-indexed patch plans after full V717 structural validation.

    Each entry is a tuple of (instruction index, target byte, source byte, size).
    Event indices, not event IDs, are used as keys. No bytes are written here.
    """
    audit(raw)
    _, _, _, ne, eo, _, io, _, _, _, _, np, po, *_ = HEAD.unpack_from(raw)
    owners = []
    result = {}
    for i in range(ne):
        _, n, off, count, p_off, _, _ = EVENT.unpack_from(raw, eo+i*EVENT.size)
        if not count:
            continue
        start = p_off//PARAMETER.size
        owners.append((start, start+count))
        items = []
        for k in range(count):
            index, target, source, width, reserved = PARAMETER.unpack_from(
                raw, po+p_off+k*PARAMETER.size)
            if not 0 <= index < n or width <= 0 or source < 0 or reserved:
                raise ValueError('invalid EMEVD substitution')
            _, _, arg_len, _, _ = INSN.unpack_from(raw, io+off+index*INSN.size)
            span(target, width, 1, arg_len)
            items.append((index, target, source, width))
        result[i] = tuple(items)
    cursor = 0
    for start, end in sorted(owners):
        if start != cursor:
            raise ValueError('parameter ownership overlap or gap')
        cursor = end
    if cursor != np:
        raise ValueError('unowned parameters')
    return result


def apply(plan, arguments, event_args):
    """Apply in file order to private copies; return only changed instructions.

    Validate source bounds against the actual invocation, not the file header.
    No caller-owned buffers are modified even if a later substitution fails.
    """
    grouped = defaultdict(list)
    for index, target, source, width in plan:
        if not 0 <= index < len(arguments) or width <= 0:
            raise ValueError('invalid EMEVD invocation')
        span(target, width, 1, len(arguments[index]))
        span(source, width, 1, len(event_args))
        grouped[index].append((target, source, width))
    result = {}
    for index, patches in grouped.items():
        out = bytearray(arguments[index])
        for target, source, width in patches:
            out[target:target+width] = event_args[source:source+width]
        result[index] = bytes(out)
    return result
