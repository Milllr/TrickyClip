import pytest
from app.services.detection_ml import detect_motion_segments, detect_segments_smart
import os

# note: these tests require actual video files to run
# skip if no test videos available

@pytest.mark.skipif(
    not os.path.exists("/tmp/test_video.mp4"),
    reason="test video not available"
)
def test_motion_detection():
    """test motion-based segment detection"""
    video_path = "/tmp/test_video.mp4"
    duration_ms = 10000  # 10 seconds
    
    segments = detect_motion_segments(video_path, duration_ms)
    
    assert isinstance(segments, list)
    assert len(segments) > 0
    
    # verify segment structure
    for start, end, confidence in segments:
        assert isinstance(start, int)
        assert isinstance(end, int)
        assert isinstance(confidence, float)
        assert 0 <= confidence <= 1.0
        assert start < end
        assert start >= 0
        assert end <= duration_ms


def test_smart_detection_fallback():
    """test that smart detection falls back gracefully on invalid video"""
    invalid_path = "/nonexistent/video.mp4"
    duration_ms = 10000
    
    # should not crash, should use fallback
    segments = detect_segments_smart(invalid_path, duration_ms)
    
    # fallback should still return something
    assert isinstance(segments, list)

