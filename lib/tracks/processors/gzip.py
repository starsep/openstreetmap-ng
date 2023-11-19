from abc import ABC

from lib.tracks.processors.base import CompressionFileProcessor


class GzipFileProcessor(CompressionFileProcessor, ABC):
    media_type = 'application/gzip'
    command = ('gzip', '-d', '-c')
