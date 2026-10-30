# Real-media evaluation

The regression suite exercises synthetic media and mocked model boundaries. It does **not** establish
transcription accuracy, editorial quality or viewer retention on real recordings. No real-person footage is
bundled: obtain explicit permission to use each recording and keep the corpus local unless redistribution
rights are separately granted.

## Corpus plan

Include EN and PT-BR recordings with quiet speech, meaningful repetition, numbers/negation, background noise,
moving/profile faces, multiple visible faces, and phone footage. Keep a held-out set. Compare unchanged
recordings and annotations across engine/VAD/tracking settings; do not tune and report on the same set.

Preserving source quality is a hard requirement: include native 60/59.94 fps, 10-bit SDR, and higher-than-1080p
recordings. Inspect native-detail crops and verify that unsupported HDR/VFR inputs are rejected rather than
silently converted. Social delivery conversions must be explicitly identified as conversions.

## Manifest

Create projects and finish their transcripts/EDLs first. Manually annotate the original recording, not its
generated transcript. Paths are relative to the manifest. Example structure (replace with actual annotations):

```json
{
  "schema_version": 1,
  "cases": [
    {
      "id": "pt-quiet-01",
      "consent_confirmed": true,
      "project": "projects/pt-quiet-01",
      "reference_words": [
        {"word": "Olá", "start": 0.1, "end": 0.4},
        {"word": "mundo", "start": 0.5, "end": 0.9}
      ],
      "expected_keep": [[0.05, 1.0]],
      "human_review": {
        "crop_failures": 1,
        "reviewed_frames": 20,
        "correction_minutes": 2.5
      }
    }
  ]
}
```

```bash
ose benchmark corpus.json --out results.json
```

The evaluator checks source/EDL provenance and requires consent confirmation. It reports word error rate,
boundary mean absolute error **only for correctly aligned words**, aligned-word coverage, seconds of wanted
speech incorrectly deleted, unwanted footage retained, transcription runtime, and supplied human crop/
correction measurements. Missing human measurements stay null, never zero or "pass".

The evaluator does not download media, run a new model automatically, or certify annotations. Repeat the
pipeline explicitly with each configuration, record the hardware/model revisions, and compare case-level
reports. `transcribe --engine faster-whisper --vad` and `--batch-size` are opt-in experiments; verify that
filler words and quiet speech survive. The default semantic model is not a guarantee of Portuguese retrieval
quality; use labeled EN/PT-BR queries to evaluate or select a multilingual OpenCLIP model.

## Review workflow

`ose review proj --reel` includes every removed source interval, including silence, with surrounding context.
A red border marks deleted material. `out/deletion_review.json` maps reel positions back to source times.
After watching, record `ose review proj --approve cut --note "..."`. Changing the EDL invalidates that approval.

Review the final render, not only its contact sheet, then use `--approve final`. Approval binds its file hash,
plan, EDL and asset bytes. QA reports missing approval as a warning separately from technical failures.
An automated pass must not imply human review or claim an unreviewed output is post-ready.

## Research references

- [uv lock/sync](https://docs.astral.sh/uv/concepts/projects/sync/)
- [OpenCV package selection](https://pypi.org/project/opencv-python/)
- [faster-whisper VAD and batching](https://github.com/SYSTRAN/faster-whisper)
- [MediaPipe video face detection](https://ai.google.dev/edge/mediapipe/solutions/vision/face_detector/python)
- [Auto-Editor measured normalization](https://auto-editor.com/docs/anorm)
- [OpenTimelineIO](https://opentimelineio.readthedocs.io/en/latest/tutorials/otio-file-format-specification.html)
- [OpenCLIP](https://github.com/mlfoundations/open_clip)
