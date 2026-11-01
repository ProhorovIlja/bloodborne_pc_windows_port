#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""V233 synthetic benchmarks conforming to original YT run_load.py fields."""
import json
from pathlib import Path
import tempfile
import yt_server_capacity_gate_v233 as gate


def fixture():
    return dict(
        players=200, playing=200, refused=0,
        packets_sent=30000, packets_received=29999, packets_lost=1,
        server_out_mbit=32.5, server_in_mbit=20.0,
        relay_ms_p99=30.0, welcome_ms_p99=250.0,
        server_cpu_avg=45.0, main_thread_cpu_avg=31.0,
        udp_buffer_drops=0, server_rss_mb_max=310.0
    )


def main():
    base=fixture()
    faster=dict(base)
    faster.update(server_out_mbit=18.0, main_thread_cpu_avg=20.0,
                  relay_ms_p99=26.0, server_rss_mb_max=280.0)
    with tempfile.TemporaryDirectory() as temp:
        root=Path(temp)
        a=root/'before.json'
        b=root/'after.json'
        a.write_text(json.dumps(base))
        b.write_text(json.dumps(faster))
        assert gate.read_one(a)==base
        good=gate.compare(gate.read_one(a),gate.read_one(b))
        assert good['all_gates_pass']
        assert not good['real_direct_p2p_verified']
        assert good['delta']['server_out_mbit']==-14.5
        slow=dict(faster, main_thread_cpu_avg=67.0)
        b.write_text(json.dumps(slow))
        failed=gate.compare(gate.read_one(a),gate.read_one(b))
        assert not failed['all_gates_pass']
        assert not failed['gates']['main_relay_thread_cpu_within_budget']
        bad=dict(faster, udp_buffer_drops=2, refused=1)
        b.write_text(json.dumps(bad))
        assert not gate.compare(base,gate.read_one(b))['all_gates_pass']
        # V237: overall VPS saturation, login stalls and loss can regress
        # while the main relay thread and outbound bandwidth improve.
        cpu_regressed=dict(faster, server_cpu_avg=80.0)
        assert not gate.compare(base,cpu_regressed)['gates']['total_server_cpu_within_budget']
        join_regressed=dict(faster, welcome_ms_p99=490.0)
        assert not gate.compare(base,join_regressed)['gates']['join_p99_within_budget']
        lost=dict(faster, packets_lost=1000)
        assert not gate.compare(base,lost)['gates']['packet_loss_rate_within_budget']
        # Normalize by generated packet volume: equal ratios are comparable.
        same_ratio=dict(faster, packets_sent=60000, packets_received=59998,
                        packets_lost=2)
        assert gate.compare(base,same_ratio)['gates']['packet_loss_rate_within_budget']
        for malformed in (dict(faster, packets_sent=0),
                          dict(faster, packets_lost=40000)):
            b.write_text(json.dumps(malformed))
            try:
                gate.read_one(b)
            except ValueError:
                pass
            else:
                raise AssertionError('invalid loss denominator/count accepted')
        uneven=dict(faster, players=150)
        try:
            gate.compare(base,uneven)
        except ValueError:
            pass
        else:
            raise AssertionError('unequal player loads allowed')
        # Refuse full logs or malformed/partial report, never truncate blindly.
        b.write_text(json.dumps(faster)+'\n'+json.dumps(faster)+'\n')
        try:
            gate.read_one(b)
        except ValueError:
            pass
        else:
            raise AssertionError('multi-line server log accepted')
        b.write_text(json.dumps(dict(faster, relay_ms_p99=float('nan'))))
        try:
            gate.read_one(b)
        except ValueError:
            pass
        else:
            raise AssertionError('non-finite benchmark accepted')
        b.write_text(json.dumps(dict(faster, playing=201)))
        try:
            gate.read_one(b)
        except ValueError:
            pass
        else:
            raise AssertionError('more played games than clients accepted')
    print('SHYT_V233_OFFICIAL_YT_SERVER_LOADTEST_COMPARE_SYNTHETIC_PASS')


if __name__ == '__main__':
    main()
