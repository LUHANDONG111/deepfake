from worker import create_detection_pipeline


def test_worker_pipeline_uses_classifier_factory(monkeypatch):
    calls = {}

    class FakeDetector:
        pass

    class FakeClassifier:
        pass

    class FakePipeline:
        def __init__(self, detector, classifier):
            calls["detector"] = detector
            calls["classifier"] = classifier

    monkeypatch.setattr("worker.OpenCVFaceDetector", FakeDetector)
    monkeypatch.setattr("worker.build_classifier", lambda model_path: FakeClassifier())
    monkeypatch.setattr("worker.DetectionPipeline", FakePipeline)

    pipeline = create_detection_pipeline("best_model.pth")

    assert isinstance(pipeline, FakePipeline)
    assert isinstance(calls["detector"], FakeDetector)
    assert isinstance(calls["classifier"], FakeClassifier)
