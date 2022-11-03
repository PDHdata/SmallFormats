# adapted from https://github.com/daggaz/json-stream/blob/0a31904354b6e731c2c3f80fe53e805cb49e9de4/src/json_stream/requests/__init__.py
# fixed in https://github.com/daggaz/json-stream/pull/28
import io

import json_stream
from json_stream.select_tokenizer import default_tokenizer


class IteratorStream(io.RawIOBase):
    def __init__(self, iterator):
        self.iterator = iterator
        self.remainder = None

    def readinto(self, buffer):
        try:
            chunk = self.remainder or next(self.iterator)
            length = min(len(buffer), len(chunk))
            buffer[:length], self.remainder = chunk[:length], chunk[length:]
            return length
        except StopIteration:
            return 0    # indicate EOF

    def readable(self):
        return True


def _to_file(response, chunk_size):
    return io.BufferedReader(IteratorStream(response.iter_bytes(chunk_size=chunk_size)))


def httpx_load(response, persistent=False, tokenizer=default_tokenizer, chunk_size=10240):
    return json_stream.load(_to_file(response, chunk_size), persistent=persistent, tokenizer=tokenizer)
