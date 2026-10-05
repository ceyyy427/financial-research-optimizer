# Finathink Bilingual Motion Reel

This is the self-contained source project for the 15-second Finathink brand motion-graphics film. It uses the installed `ruic-motion-reel` engine, code-drawn editorial motion, the two supplied Finathink product images, bilingual English/Chinese copy, and a generated 128 BPM soundtrack.

## Render

```bash
cd motion-reel
python3 -m finathink_reel.build --jobs 2
```

The verified output is:

`out/finathink_motion_reel.mp4`

The film is exactly 1920×1080, 30fps, 450 frames, and 15 seconds. `VERIFY.md` records the media and audio checks.

## Scene order

1. `FINATHINK` / `穿透金融，形成判断`
2. `FROM NOISE TO KNOWLEDGE` / `从噪声，到知识`
3. `EVIDENCE FIRST` / `先看证据，再下判断`
4. `UNDERSTAND THE WHY` / `理解背后的逻辑`
5. `TEST, DON'T GUESS` / `用量化验证，不靠猜测`
6. `BACKTEST / OUT OF SAMPLE` / `回测，也要守住样本外边界`
7. `LEARN WITH AN AGENT` / `与智能代理一起学习`
8. `THINK THROUGH FINANCE` / `把金融问题，想得更清楚`

## Notes

- The original supplied images remain in `assets/`; the `*-contrast.jpg` files are local working derivatives used to preserve detail in the light editorial grade.
- Chinese glyphs use the local macOS font path configured in `finathink_reel/theme.py`. Set `FINATHINK_CJK_FONT` to override it on another machine.
- The graph, equation, factor, backtest, and agent values are structural visual examples, not investment advice or performance claims.

