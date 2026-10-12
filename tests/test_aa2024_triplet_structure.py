import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from aa2024_triplet_structure import parse_nodemap, connection_summary


SCHEMA = "# ID; x_undef [mm]; y_undef [mm]; z_undef [mm]; u [mm]; v [mm]; w [mm]; epsx [%]; epsy [%]; epsxy [1]; epseqv [%]\n"


class TripletStructureTests(unittest.TestCase):
    def test_holdout_fields_are_not_converted(self):
        n = parse_nodemap(SCHEMA + "1;0;0;0;SEALED;SEALED;SEALED;x;x;x;x\n")
        self.assertNotIn("u", n)

    def test_fit_fields_must_parse(self):
        with self.assertRaises(ValueError):
            parse_nodemap(SCHEMA + "1;0;0;0;SEALED;0;0;0;0;0;0\n", allow_displacements=True)

    def test_nan_is_reported_not_zero_filled(self):
        n = parse_nodemap(SCHEMA + "1;nan;0;0;0;0;0;0;0;0;0\n")
        self.assertEqual(n["finite_xyz"].tolist(), [False])

    def test_duplicate_id_rejected(self):
        with self.assertRaises(ValueError):
            parse_nodemap(SCHEMA + "1;0;0;0;0;0;0;0;0;0;0\n" * 2)

    def test_connections_account_for_padding_and_zero(self):
        n = parse_nodemap(SCHEMA + "".join(f"{i};0;0;0;0;0;0;0;0;0;0\n" for i in (1, 2, 3)))
        report, t = connection_summary("Type;Element #;Node 1;Node 2;Node 3\n3;1;1;2;3\n3;2;-1;-1;-1\n3;3;1;2;0\n", n)
        self.assertEqual(report["padding_all_minus1"], 1)
        self.assertEqual(report["zero_node_rows"], 1)
        self.assertEqual(report["out_of_node_ids"], [-1, 0])
        self.assertEqual(t, {(1, 2, 3)})

    def test_duplicate_schema_and_row_width_rejected(self):
        for text in (SCHEMA + SCHEMA, SCHEMA + "1;0;0\n"):
            with self.assertRaises(ValueError):
                parse_nodemap(text)


if __name__ == "__main__":
    unittest.main()
