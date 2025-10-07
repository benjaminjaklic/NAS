import os
import ffmpeg
from flask import current_app, Response, abort
import math
import re

class VideoHandler:
    def __init__(self, file_path):
        self.file_path = file_path
        self.probe = self._probe_video()

    def _probe_video(self):
        try:
            return ffmpeg.probe(self.file_path)
        except ffmpeg.Error:
            return None

    def get_metadata(self):
        if not self.probe:
            return None
        
        video_stream = next((stream for stream in self.probe['streams'] 
                           if stream['codec_type'] == 'video'), None)
        
        if not video_stream:
            return None

        return {
            'duration': float(self.probe['format'].get('duration', 0)),
            'width': int(video_stream.get('width', 0)),
            'height': int(video_stream.get('height', 0)),
            'codec': video_stream.get('codec_name', ''),
            'bitrate': int(self.probe['format'].get('bit_rate', 0)),
            'size': int(self.probe['format'].get('size', 0))
        }

    def stream_video(self, request_range=None, quality='auto'):
        """Stream video with adaptive bitrate"""
        if not os.path.exists(self.file_path):
            abort(404)

        file_size = os.path.getsize(self.file_path)
        
        # Parse range header
        byte1, byte2 = 0, None
        if request_range:
            match = re.search(r'(\d+)-(\d*)', request_range)
            groups = match.groups()
            if groups[0]: byte1 = int(groups[0])
            if groups[1]: byte2 = int(groups[1])

        chunk_size = current_app.config['CHUNK_SIZE']
        if byte2 is None:
            byte2 = min(byte1 + chunk_size, file_size - 1)

        length = byte2 - byte1 + 1

        # Determine quality based on client's connection
        if quality == 'auto':
            quality = self._determine_quality(byte2 - byte1, length)

        def generate():
            try:
                with open(self.file_path, 'rb') as video:
                    video.seek(byte1)
                    remaining = length
                    while remaining:
                        chunk_size = min(current_app.config['CHUNK_SIZE'], remaining)
                        data = video.read(chunk_size)
                        if not data:
                            break
                        remaining -= len(data)
                        yield data
            except Exception as e:
                current_app.logger.error(f"Error streaming video: {str(e)}")
                abort(500)

        headers = {
            'Content-Range': f'bytes {byte1}-{byte2}/{file_size}',
            'Accept-Ranges': 'bytes',
            'Content-Length': str(length),
            'Content-Type': 'video/mp4',  # Adjust based on actual video type
        }

        return Response(generate(), 206, headers)

    def _determine_quality(self, bytes_read, time_taken):
        """Determine optimal quality based on client's connection speed"""
        if not time_taken:
            return 'medium'
            
        bitrate = (bytes_read * 8) / time_taken  # bits per second
        
        if bitrate > 5000000:  # 5 Mbps
            return 'high'
        elif bitrate > 2000000:  # 2 Mbps
            return 'medium'
        else:
            return 'low'

    def create_thumbnail(self, output_path, time=1):
        """Create thumbnail from video at specified time"""
        try:
            (
                ffmpeg
                .input(self.file_path, ss=time)
                .filter('scale', 480, -1)
                .output(output_path, vframes=1)
                .overwrite_output()
                .run(capture_stdout=True, capture_stderr=True)
            )
            return True
        except ffmpeg.Error:
            return False