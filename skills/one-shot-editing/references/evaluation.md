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

## Designed motion and SFX pilot

This is a separate artistic evaluation, not extra `ose benchmark` fields. Save `STYLE.md`, `STORYBOARD.md`,
selected recipe/variant revisions, cue/take metadata, frames and `REVIEW.md` in the video project.
Use the same approved cut, narration, dimensions and FPS for the old/new comparison; identify browser/delivery
conversions. Do not improve apparent results by recutting speech or selecting different excerpts.

For the data-engineering revision that motivated this integration, the candidate pilot is approximately
18.4-33 s of the existing approved cut: sources merge, logistics events become table rows.
Confirm those times against the actual current cut words before reuse; do not assume another revision has the
same timestamps. The source project is external and is not bundled here.
Compare the old output, the selected Instagram reference (a baseline, not a quality ceiling) and the new pilot.
Keep reference footage local; do not incorporate its frames or soundtrack into delivered media.

| Artistic criterion | Evidence to inspect |
| --- | --- |
| Explanation | The visible action demonstrates the spoken mechanism rather than only presenting labels. |
| Object continuity | Sources remain recognizable as records merge; events become actual rows rather than an unrelated table reveal. |
| Framing | Overlays leave usable presenter/caption space; fullscreen diagrams use the frame and return intentionally. |
| Motion | Paths agree with trajectories and perspective; entrances/actions/exits do not snap or drift accidentally. |
| Timing | Actions land on the relevant spoken words; the viewer has time to read the resulting state. |
| Restraint | No repeated top-card template, forced camera movement or effect count substituting for direction. |
| Sound | Meaningful contacts, coherent character, controlled tails and intelligible voice; silence is intentional. |

Inspect native-size frames and phone-width views, densely around movement peaks and transitions, then watch
at normal speed. A sparse contact sheet cannot certify motion. Record pass/fail/pending for each criterion,
with timestamp/frame and correction; fix the cause and rerender the same pilot before extending.

For SFX revision, export three comparisons with **identical picture**:
1. Voice only.
2. Voice plus the prior SFX.
3. Voice plus the new SFX.

Keep voice gain unchanged and music absent in all three to isolate the SFX; if the final uses music, review
that mix separately. Do not compare independently normalized variants that change voice loudness as if they
isolate sound design. Check transient-to-event offsets in the export, masking, tails and fatigue.
Listen on headphones and a phone speaker at low/normal volume; log who reviewed and what remains pending.
Earshot audits, onset measurements, model scores or existing review metadata do not constitute a listening test.

Technical acceptance remains separate: compositor checks, deterministic seeking, duration, dimensions/FPS,
asset availability, single voice, final loudness/true peak and no duplicate mix. Preserve actual compositor
evidence, never fabricate ose provenance or reuse an old render's approval.
The integration itself does not establish a higher quality score or retention; that requires this pilot and
creator review. Missing access to media, tools or listening means the corresponding evaluation is blocked/pending.

## Research references

- [uv lock/sync](https://docs.astral.sh/uv/concepts/projects/sync/)
- [OpenCV package selection](https://pypi.org/project/opencv-python/)
- [faster-whisper VAD and batching](https://github.com/SYSTRAN/faster-whisper)
- [MediaPipe video face detection](https://ai.google.dev/edge/mediapipe/solutions/vision/face_detector/python)
- [Auto-Editor measured normalization](https://auto-editor.com/docs/anorm)
- [OpenTimelineIO](https://opentimelineio.readthedocs.io/en/latest/tutorials/otio-file-format-specification.html)
- [OpenCLIP](https://github.com/mlfoundations/open_clip)
