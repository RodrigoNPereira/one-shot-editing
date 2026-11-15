# Optional Earshot SFX

Earshot supplies candidates and analysis; one-shot-editing directs sound and HyperFrames (or the explicitly
chosen FFmpeg route) mixes it. Load `earshot` only when a planned event needs procedural SFX or audio comparison.
Do not load its `real-sound` skill automatically: that is a separate recorded-audio-only production workflow.
Do not replace the user's chosen asset merely because a generator is available.

## Scope and prerequisites

When this stage is selected, automatically install the missing `earshot` skill in the current harness using
[companion setup](oss-resources.md#design-companion-setup), then load it. Installing the skill does not require
installing its Python tool until an actual CLI operation is needed; bootstrap that missing executable in an
isolated environment at that point. Announce setup and retain host permission checks; do not auto-update
existing tools. If setup or verification fails, report the blocker rather than silently skipping the cue.

Start with `sfx list/render/check`, `kit` and model-free `measure`. The procedural bank needs no model download
or GPU at render time. However the package declares Torch/Transformers dependencies: install in a separate
environment, not ose's lock-synchronized venv. Companion sources/revisions: [oss-resources.md](oss-resources.md).
Resolve the actual executable/interpreter and run `earshot doctor`; distinguish absent analysis-model caches
from a missing bank/CLI dependency. Only proceed with commands whose prerequisites are satisfied.

Model-based rank/match/describe/timeline/sheet and `forge` search are a later, opt-in scope. They can download
about 1.1 GB of models on first use. No implicit model fetch, MCP daemon, cloud critique or audio upload.
`fit` is not part of the initial route: reconstructing a recording does not remove the source's license.
Pin the tool revision and retain generated WAVs; do not update or regenerate approved takes during a render.

## Cue design before generation

After Shotcraft's visual events are timed, extend each storyboard beat with:

- Stable cue ID and purpose, or explicitly **none**.
- Exact visual event and cut-timeline time/frame; intended sync anchor (onset, peak or end).
- Source: approved existing file, licensed recording or Earshot bank member.
- Character/material, duration, tail budget, permitted variation and prohibited qualities.
- Selected take path, measured anchor, intentional lead/lag, gain and review status.

Use Earshot for stylized UI contacts, light impacts, swishes and tuned notes. Prefer licensed recordings when
real-world material identity matters (engines, footsteps, room ambience). Search/reuse good existing candidates
before generating more. Use a small coherent kit, not one effect per caption, cut or table row.
Silence is a valid decision. If an optional cue is dropped, record it; required unavailable cues remain blocked.

For Earshot candidates, inspect IDs from the installed bank rather than assuming a name exists:

```bash
earshot sfx list --kind whoosh
earshot sfx render whoosh_fast/crisp -o assets/sfx/merge.wav --dur 0.8 --apex 0.32 --seed 7
earshot sfx check assets/sfx/merge.wav
earshot measure assets/sfx/merge.wav
```

The example is a candidate, not an approved sound or default duration. Compare a few distinct takes against the
action and voice. For a reusable kit, inspect `earshot kit init --preset minimal` output before rendering it;
keep only needed roles. Neither `minimal` nor `calm` is automatic aesthetic approval. Do not use the `launch`
preset's music-relative gain, offsets or density as defaults for talking heads.

Keep the kit definition/lock or per-take reports beside `assets/sfx/`. Record source repository and revision,
bank/member ID, parameters, actual selected seed (kit retries may change it), WAV hash, measured onset/peak/end,
warnings, license/source credits and selection rationale. Preserve this metadata when ingesting into the media
ledger; do not relabel generated files as Openverse recordings or claim media-use generated them.

## Placement and one mix

Calculate `file_start = visual_event + intentional_offset - measured_anchor`, all in seconds.
Onset is suitable for a contact; the audible peak can be the anchor for a whoosh. Document exceptions rather
than copying an upstream preset's offsets. Verify synchronization again in the exported video, not just preview.

- A negative start must not be clamped silently. Prepare a trimmed copy only if its attack and intended anchor
  survive, then remeasure it; otherwise choose a shorter lead-in/different asset. Do not shift approved picture.
- Preserve tails inside the allowed interval. Trim/fade in a prepared copy or compositor and recheck for clicks.
- Do not use `kit.space_run` to push cues away from their visual events. Reduce cue density or choose which
  events remain silent instead.
- Inspect `checks`, per-take warnings and the kit lock, not just process exit status. Earshot may retain a
  warned take after retry exhaustion. Reject or explicitly review it; do not mark the entire kit approved.
- Audition gain under the actual voice; a peak-normalized WAV or music-relative `gain_db` is not a speech mix.
  Reduce/EQ/automate masking effects. Music sidechain in ose does not duck SFX.
- Use only one voice and one final mix. HyperFrames accepts local WAV clips with stable IDs and explicit
  placement/duration/gain. If using a premixed replacement, mute the source and disable duplicated SFX/music.

For the FFmpeg route, `plan.sfx` already accepts `asset` (file path), `at` (file start) and `volume_db`.
It does not support cue anchors, trimming or envelopes: prepare files first, then use the existing fields.
Keep source metadata and richer sound design outside `plan.json`. In the HyperFrames route, the storyboard
and composition own those placements; do not also burn the same effects into the browser-cut.

## Review and licensing

Run model-free checks per selected take and measure the final mix at the project's target (normally -14 LUFS,
<= -1.5 dBTP). Short SFX need envelope/peak measurements, not a forced per-effect -14 LUFS normalization.
Compare identical picture with voice-only, old SFX and new SFX when revising an existing edit; keep voice gain
and any music bed consistent. See [evaluation.md](evaluation.md#designed-motion-and-sfx-pilot).

Earshot metrics are evidence, not listening or artistic approval. Its default critique profile describes
music-led launch films, not this creator's talking head; do not use its grade as a release gate.
Model match/realness cannot prove origin, rights, quality or speech intelligibility. Preserve unperformed
headphone/phone-speaker checks as pending. A passing generated-sound audit did not prove the previous edit good.

Earshot code is MIT. Its shipped fitted entries document CC0 sources in `docs/CREDITS_FIT.md`; retain the
per-entry provenance and check rights for anything added externally. Neither MIT nor synthesis grants permission
to copy a commercial sound library or a reference Reel's soundtrack. No third-party recordings are bundled here.
