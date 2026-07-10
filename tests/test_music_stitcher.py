from services.music_stitcher import plan_music_segments, segment_prompt


def test_plan_single_segment():
    assert plan_music_segments(15.0, segment_max=30.0) == [15.0]


def test_plan_multiple_segments():
    assert plan_music_segments(65.0, segment_max=30.0) == [30.0, 30.0, 5.0]


def test_plan_exact_multiple():
    assert plan_music_segments(60.0, segment_max=30.0) == [30.0, 30.0]


def test_segment_prompt_variants():
    base = "lofi podcast intro"
    assert segment_prompt(base, 0, 3).startswith(base)
    assert "continuation" in segment_prompt(base, 1, 3)
    assert "final" in segment_prompt(base, 2, 3)
