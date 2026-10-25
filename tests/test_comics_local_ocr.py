from engine import comics_local_ocr


def test_local_ocr_module_exposes_error_type():
    assert issubclass(comics_local_ocr.LocalOcrError, RuntimeError)
