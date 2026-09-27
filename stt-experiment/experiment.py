import os
import re
import time
import statistics
import datetime
from faster_whisper import WhisperModel
import jiwer

MODELS = ["tiny", "base", "small", "medium", "large-v3-turbo"]
DEVICE = "cpu"
COMPUTE_TYPE = "int8"

SPEECH_DIR = "speech_files"

TEST_SET = [
    ("p01.aifc", "create a landing page for Maria's Bakery targeting young families"),
    ("p02.aifc", "build a page for Apex Plumbing aimed at homeowners to collect quote requests"),
    ("p03.aifc", "make a landing page for GreenLeaf Yoga Studio for busy professionals"),
    ("p04.aifc", "I want a site for Nordvik Dental Clinic with a button to book an appointment"),
    ("p05.aifc", "design a page for Lumina Photography to showcase wedding portfolios and take bookings"),
    ("p06.aifc", "launch a landing page for CodeForge Academy promoting a twelve week coding bootcamp"),
    ("p07.aifc", "set up a page for Bella Vista Trattoria so customers can reserve a table online"),
    ("p08.aifc", "create a page for PetPals Grooming targeting dog owners in Brighton"),
    ("p09.aifc", "build a landing page for Aurora Fitness offering a free seven day trial membership"),
    ("p10.aifc", "make a site for Hendricks and Pearce Law Firm focused on small business clients"),
    ("p11.aifc", "I need a page for Saffron and Sage Catering for corporate events and weddings"),
    ("p12.aifc", "create a landing page for QuantumLeap Analytics selling a subscription dashboard to startups"),
    ("p13.aifc", "build a page for Willowbrook Veterinary Hospital with an emergency contact number"),
    ("p14.aifc", "design a page for Echo Sound Studios renting rehearsal rooms to local bands"),
    ("p15.aifc", "make a landing page for Verdant Landscaping offering free garden consultations to collect leads"),
]


def normalize(text: str) -> str:
    text = text.lower()
    text = re.sub(r"[^\w\s]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


class Logger:
    def __init__(self, path):
        self.f = open(path, "w")

    def __call__(self, line=""):
        print(line)
        self.f.write(line + "\n")
        self.f.flush()

    def close(self):
        self.f.close()


def main():
    stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    log = Logger(f"results_{stamp}.log")

    log("=" * 70)
    log("STT EXPERIMENT -- faster-whisper model comparison")
    log(f"timestamp   : {stamp}")
    log(f"device      : {DEVICE}  compute_type: {COMPUTE_TYPE}")
    log(f"models      : {', '.join(MODELS)}")
    log(f"clips       : {len(TEST_SET)}")
    log("=" * 70)

    missing = [fn for fn, _ in TEST_SET if not os.path.exists(os.path.join(SPEECH_DIR, fn))]
    if missing:
        log("")
        log("ERROR: missing audio files in '%s/':" % SPEECH_DIR)
        for fn in missing:
            log("  - " + fn)
        log("Record them (see recording_script.txt) and re-run.")
        log.close()
        return

    summary = []

    for size in MODELS:
        log("")
        log(f"### MODEL: {size} " + "#" * (60 - len(size)))
        t_load = time.perf_counter()
        model = WhisperModel(size, device=DEVICE, compute_type=COMPUTE_TYPE)
        log(f"  (loaded in {time.perf_counter() - t_load:.1f}s)")

        warm_path = os.path.join(SPEECH_DIR, TEST_SET[0][0])
        warm_segs, _ = model.transcribe(warm_path)
        _ = " ".join(s.text for s in warm_segs)

        wers, latencies, rtfs = [], [], []

        for fname, reference in TEST_SET:
            audio_path = os.path.join(SPEECH_DIR, fname)

            t0 = time.perf_counter()
            segments, info = model.transcribe(audio_path)
            hypothesis = " ".join(s.text for s in segments).strip()
            latency = time.perf_counter() - t0

            duration = getattr(info, "duration", None) or 0.0
            rtf = (latency / duration) if duration else float("nan")
            wer = jiwer.wer(normalize(reference), normalize(hypothesis))

            wers.append(wer)
            latencies.append(latency)
            if duration:
                rtfs.append(rtf)

            log("")
            log(f"  [{fname}]  WER={wer:.3f}  latency={latency:.2f}s  "
                f"RTF={rtf:.2f}  dur={duration:.1f}s")
            log(f"     ref : {reference}")
            log(f"     hyp : {hypothesis}")

        log("")
        log(f"  -- {size} means: WER={statistics.mean(wers):.3f}  "
            f"latency={statistics.mean(latencies):.2f}s  "
            f"RTF={statistics.mean(rtfs):.2f}" if rtfs else
            f"  -- {size} means: WER={statistics.mean(wers):.3f}  "
            f"latency={statistics.mean(latencies):.2f}s")

        summary.append((
            size,
            statistics.mean(wers) if wers else float("nan"),
            statistics.mean(latencies) if latencies else float("nan"),
            statistics.mean(rtfs) if rtfs else float("nan"),
        ))

    log("")
    log("=" * 70)
    log("SUMMARY (means per model)")
    log("=" * 70)
    log(f"{'model':<10}{'mean_WER':<12}{'mean_lat_s':<14}{'mean_RTF':<10}")
    log("-" * 46)
    for size, mwer, mlat, mrtf in summary:
        log(f"{size:<10}{mwer:<12.3f}{mlat:<14.2f}{mrtf:<10.2f}")
    log("=" * 70)
    log("Tip: scan the 'hyp' lines above for misheard business names --")
    log("those are the qualitative failure cases worth quoting in the report.")

    log.close()


if __name__ == "__main__":
    main()
