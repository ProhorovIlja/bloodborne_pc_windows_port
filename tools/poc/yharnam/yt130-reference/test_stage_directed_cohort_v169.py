"""Source-locked synthetic directions for original YT1.3 bbload, no private IDs."""
import json
from types import SimpleNamespace
from textwrap import dedent
import unittest
import stage_directed_cohort_v169 as v


def worker(n=5,seconds=range(10,40),entries=40):
    rows=[]
    agg=[]
    for sec in seconds:
        sent=received=0
        for src in range(n):
            for dst in range(n):
                if src==dst:
                    continue
                rows.append(dict(start_us=sec*1_000_000,route=src*n+dst,
                                 sent_entries=entries,received_entries=entries))
                sent += entries
                received += entries
        agg.append(dict(start_us=sec*1_000_000,
                        sent_entries=sent,received_entries=received))
    return {"cohort_directed_entries":rows,"cohort_unknown_senders":0,
            "cohort_epoch_entries":agg}


def evaluate(workers,per=None):
    if per is None:per=[1]*len(workers)
    cohort_sent=sum(row['sent_entries'] for w in workers
                    for row in w['cohort_epoch_entries'])
    cohort_received=sum(row['received_entries'] for w in workers
                        for row in w['cohort_epoch_entries'])
    ns={'cohort_quality':'GLOBAL_GAME_COHORT_PASS_DIAGNOSTIC_ONLY',
        'cohort_start_us':10_000_000,'cohort_end_us':40_000_000,
        'cohort_sent':cohort_sent,'cohort_received':cohort_received,
        'results':workers,'args':SimpleNamespace(team_size=5),'per':per}
    exec(dedent(v.DIRECTED_AGG),ns)
    return ns


class DirectedSource(unittest.TestCase):
    def test_cpp_source_exact_and_no_identity_output(self):
        src=('SHYT_V161_GLOBAL_COHORT_SEND_TIMESTAMP_BUCKETS\n'
             'SHYT_V158_NATIVE_QT_RECEIVE_DIAGNOSTICS\n'+
             v.CLASS_OLD+v.SEND_OLD+v.RECEIVED_OLD+v.FINISH_OLD+v.JSON_OLD)
        candidate=v.patch_cpp(src)
        self.assertIn(v.MARK,candidate)
        self.assertIn('load.NameOf(team, candidate)',candidate)
        self.assertIn('"route", static_cast<double>(key.second)',candidate)
        self.assertNotIn('"online_id"',candidate)
        self.assertNotIn('"sender_name"',candidate)
        self.assertNotIn('"ip"',candidate)
        with self.assertRaises(ValueError):v.patch_cpp(candidate)
    def test_python_shards_source_exact(self):
        src=('SHYT_V161_GLOBAL_COHORT_SEND_TIMESTAMP_BUCKETS\n'
             'if load.returncode != 0 or len(child_rows) != 1:\n'+
             v.RUN_ANCHOR+v.SUMMARY_OLD)
        patched=v.patch_shards(src)
        self.assertIn('directed_routes',patched)
        self.assertIn('cohort_directed_entries',patched)
        with self.assertRaises(ValueError):v.patch_shards(patched)
    def test_valid_directed_5_seat_flow(self):
        w=worker()
        x=evaluate([w,worker()])
        self.assertEqual(x['directed_quality'],'DIRECTED_GAME_COHORT_PASS_DIAGNOSTIC_ONLY')
        self.assertEqual(x['directed_sent'],x['cohort_sent'])
        self.assertEqual(x['directed_routes'],40)
    def test_isolated_low_volume_loss_not_hidden_by_global_delivery(self):
        w=worker()
        z=worker()
        z['cohort_directed_entries'][4]['received_entries']=0
        z['cohort_epoch_entries'][0]['received_entries']-=40
        x=evaluate([w,z])
        self.assertGreater(x['cohort_received']*100,x['cohort_sent']*99)
        self.assertEqual(x['directed_quality'],'DIRECTED_GAME_COHORT_DELIVERY_DEGRADED')
    def test_real_200_hunter_40_team_800_flow_shape(self):
        # Four original Qt children, ten complete five-seat teams each,
        # 800 directed flows over thirty synchronized full seconds.
        one=worker()
        chunks=[]
        for _ in range(4):
            rows=[dict(entry,route=entry["route"]+25*team)
                  for team in range(10)
                  for entry in one["cohort_directed_entries"]]
            epochs=[dict(entry,sent_entries=entry["sent_entries"]*10,
                         received_entries=entry["received_entries"]*10)
                    for entry in one["cohort_epoch_entries"]]
            chunks.append({"cohort_directed_entries":rows,
                           "cohort_unknown_senders":0,
                           "cohort_epoch_entries":epochs})
        self.assertEqual(sum(len(x["cohort_directed_entries"]) for x in chunks),24000)
        result=evaluate(chunks,per=[10]*4)
        self.assertEqual(result["directed_routes"],800)
        self.assertEqual(result["directed_quality"],
                         "DIRECTED_GAME_COHORT_PASS_DIAGNOSTIC_ONLY")
        chunks[-1]["cohort_directed_entries"].pop()
        self.assertEqual(evaluate(chunks,per=[10]*4)["directed_quality"],
                         "INVALID_DIRECTED_GAME_COHORT")

    def test_missing_extra_and_invalid_routes_fail_closed(self):
        good=worker()
        cases=[]
        a=worker();a['cohort_directed_entries'].pop();cases.append(a)
        a=worker();a['cohort_directed_entries'].append(dict(a['cohort_directed_entries'][0]));cases.append(a)
        a=worker();a['cohort_directed_entries'][0]['route']=0;cases.append(a)
        a=worker();a['cohort_directed_entries'][0]['received_entries']=9999;cases.append(a)
        a=worker();a['cohort_unknown_senders']=1;cases.append(a)
        a=worker();a['cohort_directed_entries'][0]['start_us']=float('nan');cases.append(a)
        for n,a in enumerate(cases):
            with self.subTest(case=n):
                x=evaluate([good,a])
                self.assertEqual(x['directed_quality'],'INVALID_DIRECTED_GAME_COHORT')


if __name__=='__main__':unittest.main()
