"""V182: original hosted 200-player JSON must retain only validated Qt buffer sizes."""
import importlib.util
from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parent

def load(name,tag):
    spec=importlib.util.spec_from_file_location(tag,ROOT/name)
    mod=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

grade=load("run_five_hunter_shards_v117.py","grade_v182")
sample=load("test_shard_five_v117.py","fixture_v182")

SCOPE=("one numeric bind report per original Qt shard; kernel effective values, "
       "NOT per-socket packet losses or production QoS")

def with_readback(shards=1):
    item=sample.sample(shards)
    item["per_shard"]=[dict(x) for x in item["per_shard"]]
    for index,row in enumerate(item["per_shard"]):
        row.update(udp_socket_requested_bytes=16777216,
                   udp_socket_effective_receive_bytes=425984+index,
                   udp_socket_effective_send_bytes=425984+index,
                   udp_socket_bind_reports=1,
                   udp_socket_readback_valid=True)
    item.update(udp_socket_readback_complete=True,
                udp_socket_min_effective_receive_bytes=425984,
                udp_socket_min_effective_send_bytes=425984,
                udp_socket_readback_scope=SCOPE)
    return item

class QtSocketReadbackEvidenceTests(unittest.TestCase):
    def test_actual_grade_retains_every_shard_and_summary(self):
        for shards in (1,3):
            item=with_readback(shards)
            result=grade.grade(item,shards)
            self.assertNotIn("READBACK",result["quality"])
            self.assertTrue(result["udp_socket_readback_complete"])
            self.assertEqual(result["udp_socket_min_effective_receive_bytes"],425984)
            self.assertEqual(len(result["per_shard"]),shards)
            self.assertTrue(all(r["udp_socket_readback_valid"] for r in result["per_shard"]))
            self.assertEqual(result["udp_socket_readback_scope"],SCOPE)
            self.assertNotIn("player_ip",str(result))
            self.assertNotIn("online_id",str(result))

    def test_bad_scope_and_invalid_numeric_counter_rejected(self):
        item=with_readback()
        item["udp_socket_readback_complete"]=1
        self.assertEqual(grade.grade(item,1)["quality"],
                         "INVALID_QT_UDP_SOCKET_READBACK_SCOPE")
        item=with_readback()
        item["udp_socket_min_effective_receive_bytes"]=0
        self.assertEqual(grade.grade(item,1)["quality"],
                         "QT_UDP_SOCKET_READBACK_TOTAL_MISMATCH")
        item=with_readback()
        item["per_shard"][0]["udp_socket_bind_reports"]=True
        self.assertEqual(grade.grade(item,1)["quality"],
                         "INVALID_QT_UDP_SOCKET_READBACK_SHARD")

    def test_missing_or_duplicate_bind_cannot_greenwash_qos(self):
        item=with_readback()
        item["udp_socket_readback_complete"]=False
        item["per_shard"][0]["udp_socket_readback_valid"]=False
        item["per_shard"][0]["udp_socket_bind_reports"]=2
        result=grade.grade(item,1)
        self.assertFalse(result["udp_socket_readback_complete"])
        self.assertNotEqual(result["quality"],"FULL_GAMEPLAY_SYNTHETIC_ONLY")
        # Older reports without V182 remain compatible and do not invent a readback.
        prior=grade.grade(sample.sample(1),1)
        self.assertNotIn("udp_socket_min_effective_receive_bytes",prior)

if __name__=="__main__":unittest.main()
