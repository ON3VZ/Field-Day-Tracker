"""
tests/test_n1mm_parser.py
==========================
Unit tests for app.integrations.n1mm_parser

Uses realistic N1MM Logger+ XML Contact broadcast samples.

Run with:
    python -m unittest tests.test_n1mm_parser -v
"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.integrations.n1mm_parser import N1MMParser, _parse_timestamp


# ---------------------------------------------------------------------------
# Sample N1MM XML payloads
# ---------------------------------------------------------------------------

CONTACT_40M_CW = """<contactinfo>
    <app>N1MM</app>
    <contestname>FDREG1</contestname>
    <timestamp>2025-06-21 10:30:00</timestamp>
    <call>ON3VZ</call>
    <band>40M</band>
    <rxfreq>703000</rxfreq>
    <txfreq>703000</txfreq>
    <mode>CW</mode>
    <ID>1234567890</ID>
    <operator>ON3VZ</operator>
    <mycall>ON0TEST</mycall>
    <IsRunQSO>1</IsRunQSO>
    <StationName>Radio1</StationName>
</contactinfo>"""

CONTACT_80M_SSB = """<contactinfo>
    <app>N1MM</app>
    <contestname>FDREG1</contestname>
    <timestamp>2025-06-21 14:00:00</timestamp>
    <call>ON4ABC</call>
    <band>80M</band>
    <rxfreq>358000</rxfreq>
    <txfreq>358000</txfreq>
    <mode>SSB</mode>
    <ID>9876543210</ID>
    <operator>ON4ABC</operator>
    <mycall>ON0TEST</mycall>
</contactinfo>"""

CONTACT_PORTABLE_CALL = """<contactinfo>
    <app>N1MM</app>
    <contestname>FDREG1</contestname>
    <timestamp>2025-06-21 11:00:00</timestamp>
    <call>ON3VZ/P</call>
    <band>40M</band>
    <rxfreq>703500</rxfreq>
    <txfreq>703500</txfreq>
    <mode>CW</mode>
    <ID>1111111111</ID>
    <mycall>ON0TEST</mycall>
</contactinfo>"""

CONTACT_NO_BAND_HAS_FREQ = """<contactinfo>
    <app>N1MM</app>
    <contestname>FDREG1</contestname>
    <timestamp>2025-06-21 12:00:00</timestamp>
    <call>ON5XY</call>
    <band></band>
    <rxfreq>1420000</rxfreq>
    <mode>SSB</mode>
    <ID>2222222222</ID>
    <mycall>ON0TEST</mycall>
</contactinfo>"""

CONTACT_2M = """<contactinfo>
    <app>N1MM</app>
    <contestname>FDREG1</contestname>
    <timestamp>2025-06-21 15:00:00</timestamp>
    <call>ON6YY</call>
    <band>2M</band>
    <rxfreq>14550000</rxfreq>
    <txfreq>14550000</txfreq>
    <mode>FM</mode>
    <ID>3333333333</ID>
    <mycall>ON0TEST</mycall>
</contactinfo>"""

# Non-contact broadcast (score update — should be ignored)
SCORE_MESSAGE = """<score>
    <app>N1MM</app>
    <contestname>FDREG1</contestname>
    <totalScore>1500</totalScore>
</score>"""

# Malformed XML
MALFORMED_XML = "<contactinfo><call>ON3VZ</call BROKEN"

# Empty string
EMPTY = ""

# Valid XML but not a contact
OTHER_XML = "<radio><freq>7030000</freq></radio>"


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestN1MMParserBasic(unittest.TestCase):

    def test_parse_40m_cw_contact(self):
        qso = N1MMParser.parse(CONTACT_40M_CW)
        self.assertIsNotNone(qso)
        self.assertEqual(qso.original_callsign, "ON3VZ")
        self.assertEqual(qso.normalized_callsign, "ON3VZ")
        self.assertEqual(qso.band, "40m")
        self.assertEqual(qso.mode, "CW")
        self.assertEqual(qso.n1mm_id, "1234567890")
        self.assertEqual(qso.contest_name, "FDREG1")
        self.assertEqual(qso.source, "n1mm_udp")

    def test_parse_80m_ssb_contact(self):
        qso = N1MMParser.parse(CONTACT_80M_SSB)
        self.assertIsNotNone(qso)
        self.assertEqual(qso.original_callsign, "ON4ABC")
        self.assertEqual(qso.band, "80m")
        self.assertEqual(qso.mode, "SSB")

    def test_timestamp_parsed_as_utc_iso(self):
        qso = N1MMParser.parse(CONTACT_40M_CW)
        self.assertIsNotNone(qso)
        self.assertIn("2025-06-21", qso.timestamp_utc)
        self.assertIn("10:30:00", qso.timestamp_utc)
        # Should be UTC-aware
        from datetime import datetime
        dt = datetime.fromisoformat(qso.timestamp_utc)
        self.assertIsNotNone(dt.tzinfo)

    def test_frequency_converted_from_n1mm_units(self):
        # rxfreq=703000 in N1MM = 703000 × 10 = 7_030_000 Hz = 7.030 MHz
        qso = N1MMParser.parse(CONTACT_40M_CW)
        self.assertIsNotNone(qso)
        self.assertAlmostEqual(qso.frequency_hz, 7_030_000.0)

    def test_raw_message_stored(self):
        qso = N1MMParser.parse(CONTACT_40M_CW)
        self.assertIsNotNone(qso)
        self.assertIn("ON3VZ", qso.raw_message)

    def test_source_is_n1mm_udp(self):
        qso = N1MMParser.parse(CONTACT_40M_CW)
        self.assertEqual(qso.source, "n1mm_udp")


class TestN1MMParserCallsignNormalisation(unittest.TestCase):

    def test_portable_call_nonstrict(self):
        qso = N1MMParser.parse(CONTACT_PORTABLE_CALL, strict=False)
        self.assertIsNotNone(qso)
        self.assertEqual(qso.original_callsign, "ON3VZ/P")
        self.assertEqual(qso.normalized_callsign, "ON3VZ")

    def test_portable_call_strict(self):
        qso = N1MMParser.parse(CONTACT_PORTABLE_CALL, strict=True)
        self.assertIsNotNone(qso)
        self.assertEqual(qso.original_callsign, "ON3VZ/P")
        self.assertEqual(qso.normalized_callsign, "ON3VZ/P")

    def test_original_callsign_always_preserved(self):
        qso = N1MMParser.parse(CONTACT_PORTABLE_CALL, strict=False)
        self.assertEqual(qso.original_callsign, "ON3VZ/P")


class TestN1MMParserBandResolution(unittest.TestCase):

    def test_band_from_field(self):
        qso = N1MMParser.parse(CONTACT_40M_CW)
        self.assertEqual(qso.band, "40m")

    def test_band_from_frequency_when_field_empty(self):
        # rxfreq=1420000 → 14_200_000 Hz → 20m
        qso = N1MMParser.parse(CONTACT_NO_BAND_HAS_FREQ)
        self.assertIsNotNone(qso)
        self.assertEqual(qso.band, "20m")

    def test_2m_band(self):
        qso = N1MMParser.parse(CONTACT_2M)
        self.assertIsNotNone(qso)
        self.assertEqual(qso.band, "2m")

    def test_80m_frequency_conversion(self):
        # rxfreq=358000 → 3_580_000 Hz → 80m
        qso = N1MMParser.parse(CONTACT_80M_SSB)
        self.assertAlmostEqual(qso.frequency_hz, 3_580_000.0)
        self.assertEqual(qso.band, "80m")


class TestN1MMParserEdgeCases(unittest.TestCase):

    def test_bytes_input(self):
        qso = N1MMParser.parse(CONTACT_40M_CW.encode("utf-8"))
        self.assertIsNotNone(qso)
        self.assertEqual(qso.original_callsign, "ON3VZ")

    def test_score_message_returns_none(self):
        qso = N1MMParser.parse(SCORE_MESSAGE)
        self.assertIsNone(qso)

    def test_malformed_xml_returns_none(self):
        qso = N1MMParser.parse(MALFORMED_XML)
        self.assertIsNone(qso)

    def test_empty_string_returns_none(self):
        qso = N1MMParser.parse(EMPTY)
        self.assertIsNone(qso)

    def test_other_xml_returns_none(self):
        qso = N1MMParser.parse(OTHER_XML)
        self.assertIsNone(qso)

    def test_is_contact_message_true(self):
        self.assertTrue(N1MMParser.is_contact_message(CONTACT_40M_CW))

    def test_is_contact_message_false_for_score(self):
        self.assertFalse(N1MMParser.is_contact_message(SCORE_MESSAGE))

    def test_is_contact_message_bytes(self):
        self.assertTrue(
            N1MMParser.is_contact_message(CONTACT_40M_CW.encode("utf-8"))
        )

    def test_no_call_returns_none(self):
        xml = """<contactinfo>
            <timestamp>2025-06-21 10:00:00</timestamp>
            <band>40M</band>
            <mode>CW</mode>
        </contactinfo>"""
        self.assertIsNone(N1MMParser.parse(xml))

    def test_no_timestamp_returns_none(self):
        xml = """<contactinfo>
            <call>ON3VZ</call>
            <band>40M</band>
            <mode>CW</mode>
        </contactinfo>"""
        self.assertIsNone(N1MMParser.parse(xml))

    def test_whitespace_only_returns_none(self):
        self.assertIsNone(N1MMParser.parse("   "))

    def test_case_insensitive_tags(self):
        """N1MM sometimes varies tag capitalisation."""
        xml = """<contactinfo>
            <TIMESTAMP>2025-06-21 10:30:00</TIMESTAMP>
            <CALL>ON3VZ</CALL>
            <Band>40M</Band>
            <MODE>CW</MODE>
            <ID>999</ID>
        </contactinfo>"""
        qso = N1MMParser.parse(xml)
        self.assertIsNotNone(qso)
        self.assertEqual(qso.original_callsign, "ON3VZ")


class TestParseTimestamp(unittest.TestCase):

    def test_standard_n1mm_format(self):
        result = _parse_timestamp("2025-06-21 10:30:00")
        self.assertIsNotNone(result)
        self.assertIn("2025-06-21", result)
        self.assertIn("10:30:00", result)

    def test_empty_returns_none(self):
        self.assertIsNone(_parse_timestamp(""))

    def test_invalid_returns_none(self):
        self.assertIsNone(_parse_timestamp("not-a-date"))

    def test_result_is_utc_aware(self):
        result = _parse_timestamp("2025-06-21 10:30:00")
        from datetime import datetime
        dt = datetime.fromisoformat(result)
        self.assertIsNotNone(dt.tzinfo)


if __name__ == "__main__":
    unittest.main()
