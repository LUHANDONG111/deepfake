import os

import pytest

from report_analysis import analyze_report


def test_analyze_report_computes_summary_and_top_risk_segments(tmp_path):
    report_path = os.path.join(tmp_path, "report.csv")
    with open(report_path, "w", encoding="utf-8", newline="") as file:
        file.write("frame_index,timestamp,face_count,raw_score,smoothed_score,verdict,boxes\n")
        file.write('0,0.0000,1,0.200000,0.200000,REAL,"[[10, 10, 60, 60]]"\n')
        file.write('2,0.0800,1,0.900000,0.700000,FAKE,"[[12, 12, 62, 62]]"\n')
        file.write('4,0.1600,0,0.400000,0.500000,FAKE,[]\n')
        file.write('6,0.2400,1,0.800000,0.900000,FAKE,"[[14, 14, 64, 64]]"\n')

    analysis = analyze_report(report_path, risk_limit=2)

    assert analysis["summary"]["sampled_frames"] == 4
    assert analysis["summary"]["face_frames"] == 3
    assert analysis["summary"]["fake_frames"] == 3
    assert analysis["summary"]["real_frames"] == 1
    assert analysis["summary"]["fake_ratio"] == pytest.approx(0.75)
    assert analysis["summary"]["real_ratio"] == pytest.approx(0.25)
    assert analysis["summary"]["max_raw_score"] == pytest.approx(0.9)
    assert analysis["summary"]["max_smoothed_score"] == pytest.approx(0.9)
    assert analysis["summary"]["highest_risk_time"] == pytest.approx(0.24)
    assert analysis["summary"]["highest_risk_frame"] == 6
    assert [row["frame_index"] for row in analysis["risk_segments"]] == [6, 2]
    assert analysis["timeline"][0]["boxes"] == [[10, 10, 60, 60]]
    assert analysis["risk_segments"][0]["boxes"] == [[14, 14, 64, 64]]


def test_analyze_report_skips_malformed_rows(tmp_path):
    report_path = os.path.join(tmp_path, "report.csv")
    with open(report_path, "w", encoding="utf-8", newline="") as file:
        file.write("frame_index,timestamp,face_count,raw_score,smoothed_score,verdict\n")
        file.write("0,0.0000,1,0.200000,0.200000,REAL\n")
        file.write("bad,0.0800,1,0.900000,0.700000,FAKE\n")
        file.write("4,broken,1,0.400000,0.500000,FAKE\n")

    analysis = analyze_report(report_path)

    assert len(analysis["timeline"]) == 1
    assert analysis["summary"]["sampled_frames"] == 1
    assert analysis["summary"]["real_frames"] == 1
    assert analysis["timeline"][0]["boxes"] == []


def test_analyze_report_returns_empty_analysis_for_missing_report(tmp_path):
    analysis = analyze_report(os.path.join(tmp_path, "missing.csv"))

    assert analysis["timeline"] == []
    assert analysis["risk_segments"] == []
    assert analysis["summary"]["sampled_frames"] == 0
    assert analysis["summary"]["highest_risk_time"] is None
