# Media Production

When the task involves video editing, rendering, or AI-generated media:

## Local toolchain

1. **ffmpeg** — cut, concat, transcode, extract audio, burn subtitles
2. **Remotion** — programmatic React-based video (npm project)
3. **Python + moviepy** — quick edits when React is overkill

## AI media platforms (reference workflows)

- **Higgsfield.ai** — AI video/image generation (browser workflow)
- **Palmier** — AI-native video editor (Claude-integrated)

For AI platform tasks, use web automation skill to navigate and export assets, then ffmpeg for post-processing.

## Slice patterns

| Task | Stack | Output |
|------|-------|--------|
| Clip assembly | ffmpeg | `output.mp4` |
| Branded intro | Remotion | `out/video.mp4` |
| Captions | ffmpeg + SRT | `captioned.mp4` |
| Thumbnail | ffmpeg or Pillow | `thumb.jpg` |

## Validation

- `ffprobe` confirms duration, resolution, codec
- Output file size > 10 KB
- For Remotion: `npm run build` succeeds

## Registry conventions

- `VideoRenderer`, `MediaPipeline`, `CaptionTrack`
- Assets in `media/` or `assets/video/`
