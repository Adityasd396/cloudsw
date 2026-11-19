"""Create synthetic audit media locally; requires an existing FFmpeg executable."""
from pathlib import Path
import shutil,subprocess
root=Path(__file__).resolve().parents[1];output=root/'.openai/stream-audit/media';output.mkdir(parents=True,exist_ok=True)
ffmpeg=shutil.which('ffmpeg')
if not ffmpeg:raise SystemExit('FFmpeg is unavailable. No installation was attempted.')
subprocess.run([ffmpeg,'-hide_banner','-loglevel','error','-y','-f','lavfi','-i','testsrc2=size=640x360:rate=30','-f','lavfi','-i','sine=frequency=440:sample_rate=44100','-t','18','-c:v','libx264','-preset','veryfast','-crf','23','-g','30','-pix_fmt','yuv420p','-c:a','aac','-b:a','64k','-movflags','+faststart',str(output/'clip.mp4')],check=True)
subprocess.run([ffmpeg,'-hide_banner','-loglevel','error','-y','-i',str(output/'clip.mp4'),'-c','copy','-hls_time','2','-hls_list_size','0','-hls_segment_filename',str(output/'part-%02d.ts'),str(output/'clip.m3u8')],check=True)
print('Created synthetic MP4 and HLS fixtures; no user media was read.')
