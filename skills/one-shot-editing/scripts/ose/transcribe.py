"""Word-level transcription (faster-whisper by default, WhisperX when installed and requested)."""
from __future__ import annotations

import math
import time

from .common import OseError, Project, ffmpeg, log, read_json, write_json
from .provenance import digest

# Prompting Whisper with disfluent text makes it keep "um"/"uh" instead of silently cleaning them,
# which is what lets the rough cut find and remove filler words.
DISFLUENT_PROMPT = {
    "en": "Umm, so, uh, I was like, hmm, thinking... you know, uh, let me, let me say that again.",
    "pt": "Ééé, então, hã, tipo assim, hum... né, ahn, deixa eu, deixa eu falar de novo.",
    "es": "Eh, este, o sea, mmm, pues... bueno, eh, déjame, déjame decirlo otra vez.",
}


def extract_audio(src, dst) -> None:
    ffmpeg(["-i", src, "-vn", "-ac", "1", "-ar", "16000", "-c:a", "pcm_s16le", dst])


def transcribe_faster_whisper(audio, language, model_name, keep_fillers, *, vad=False, batch_size=None):
    from faster_whisper import WhisperModel

    model = WhisperModel(model_name, device="auto", compute_type="int8")
    prompt = DISFLUENT_PROMPT.get((language or "en")[:2]) if keep_fillers else None
    import soundfile as sf

    samples, _ = sf.read(str(audio), dtype="float32")  # 16 kHz mono wav; avoids PyAV version issues
    if batch_size:
        from faster_whisper import BatchedInferencePipeline
        model = BatchedInferencePipeline(model)
    options = {"batch_size": batch_size} if batch_size else {}
    segments, info = model.transcribe(
        samples,
        language=language,
        word_timestamps=True,
        initial_prompt=prompt,
        condition_on_previous_text=False,
        vad_filter=vad,
        beam_size=5,
        **options,
    )
    words, segs = [], []
    for s in segments:
        segs.append({"start": round(s.start, 3), "end": round(s.end, 3), "text": s.text.strip()})
        for w in s.words or []:
            text = w.word.strip()
            if text:
                words.append({"word": text, "start": round(w.start, 3), "end": round(w.end, 3),
                              "prob": round(w.probability, 3)})
    return words, segs, info.language, round(info.language_probability, 3)


def transcribe_whisperx(audio, language, model_name, keep_fillers):
    import whisperx

    device = "cpu"
    try:
        import torch
        device = "cuda" if torch.cuda.is_available() else "cpu"
    except Exception:
        pass
    asr_opts = {"initial_prompt": DISFLUENT_PROMPT.get((language or "en")[:2])} if keep_fillers else {}
    model = whisperx.load_model(model_name, device, compute_type="int8" if device == "cpu" else "float16",
                                language=language, asr_options=asr_opts)
    aud = whisperx.load_audio(str(audio))
    result = model.transcribe(aud, batch_size=8)
    lang = result.get("language", language)
    align_model, meta = whisperx.load_align_model(language_code=lang, device=device)
    aligned = whisperx.align(result["segments"], align_model, meta, aud, device, return_char_alignments=False)
    words, segs = [], []
    for s in aligned["segments"]:
        if s["text"].strip() and not s.get("words"):
            raise OseError(f"WhisperX could not align segment {s['text']!r}; retry with --engine faster-whisper")
        segs.append({"start": round(s["start"], 3), "end": round(s["end"], 3), "text": s["text"].strip()})
        for w in s.get("words", []):
            text = w.get("word", "").strip()
            if not text:
                continue
            start, end = w.get("start"), w.get("end")
            if (start is None or end is None or not math.isfinite(start) or not math.isfinite(end)
                    or not 0 <= start < end):
                raise OseError(f"WhisperX could not align word {text!r}; retry transcription with --engine faster-whisper "
                               "or correct the transcript. No words were silently dropped.")
            words.append({"word": text, "start": round(start, 3), "end": round(end, 3),
                          "prob": round(w.get("score") or 0.0, 3)})
    return words, segs, lang, None


def run_transcribe(project: Project, *, language=None, model="small", engine="auto", keep_fillers=True,
                   vad=False, batch_size=None) -> dict:
    project.require()
    if batch_size is not None and batch_size <= 0:
        raise OseError("batch size must be positive")
    if batch_size and not vad:
        raise OseError("batched transcription requires explicit --vad; inspect quiet speech and filler coverage")
    project.work.mkdir(parents=True, exist_ok=True)
    audio = project.work / "audio16k.wav"
    source_hash = digest(project.source)
    audio_record = project.work / "audio.provenance.json"
    cached_audio = read_json(audio_record, {})
    if (not audio.exists() or cached_audio.get("source_sha256") != source_hash or
            cached_audio.get("audio_sha256") != digest(audio)):
        log("extracting audio")
        extract_audio(project.source, audio)
        write_json(audio_record, {"source_sha256": source_hash, "audio_sha256": digest(audio)})

    language = language or project.meta.get("language") or None
    if engine == "auto":
        try:
            import whisperx  # noqa: F401
            engine = "whisperx"
        except ImportError:
            engine = "faster-whisper"
    t0 = time.time()
    log(f"transcribing with {engine} ({model}, language={language or 'auto'})")
    if engine == "whisperx":
        if vad or batch_size:
            raise OseError("--vad/--batch-size require --engine faster-whisper")
        words, segs, lang, lang_p = transcribe_whisperx(audio, language, model, keep_fillers)
    elif engine == "faster-whisper":
        words, segs, lang, lang_p = transcribe_faster_whisper(audio, language, model, keep_fillers,
                                                           vad=vad, batch_size=batch_size)
    else:
        raise OseError(f"unknown engine {engine}")
    if not words:
        raise OseError("no speech detected")

    if digest(project.source) != source_hash:
        raise OseError("source changed during transcription; retry on an immutable source")
    data = {"engine": engine, "model": model, "language": lang, "language_probability": lang_p,
            "source_sha256": source_hash, "options": {"keep_fillers": keep_fillers, "vad": vad, "batch_size": batch_size},
            "words": words, "segments": segs, "elapsed_s": round(time.time() - t0, 1)}
    write_json(project.transcript, data)
    project.update_meta(language=lang)
    log(f"{len(words)} words, language={lang}, {data['elapsed_s']}s -> {project.transcript}")
    return data
