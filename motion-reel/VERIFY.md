# Finathink Motion Reel Verification

Verified on 2026-10-04 from the local `motion-reel/` project.

## Deliverable

- File: `out/finathink_motion_reel.mp4`
- Video: H.264, 1920×1080, 30/1 fps, 450 frames
- Duration: 15.000000 seconds
- Audio: AAC, stereo, 48 kHz

## Audio check

The decoded `loudnorm=print_format=summary` check reported:

- Input Integrated: `-9.4 LUFS`
- Input True Peak: `-0.9 dBTP`
- Output Integrated: `-23.7 LUFS`
- Output True Peak: `-15.4 dBTP`

The source mix stays below 0 dBTP.

## Visual check

Representative frames were extracted at 0.5s, 2.5s, 4.5s, 6.5s, 8.5s, 10.5s, 12.5s, and 14.5s into `out/representative/`. They were inspected for:

- readable English headlines and Chinese supporting copy;
- the opening research workspace image and architecture map;
- evidence, knowledge, quant, out-of-sample, and learning-agent chapters;
- preserved light-editorial contrast without bloom washout;
- visible frame-to-frame scene progression and safe margins.

## Commands

```bash
cd motion-reel
python3 -m finathink_reel.build --jobs 2
python3 -m pytest tests -q
```

