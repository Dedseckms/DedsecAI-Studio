import struct

def gguf_info(path):
    """Read scalar GGUF metadata, skip arrays without loading model weights."""
    formats = {0:'B', 1:'b', 2:'H', 3:'h', 4:'I', 5:'i', 6:'f', 7:'?', 10:'Q', 11:'q', 12:'d'}
    file_size=path.stat().st_size
    with path.open('rb') as src:
        def unpack(fmt):
            return struct.unpack('<'+fmt, src.read(struct.calcsize('<'+fmt)))[0]
        def string(keep=True):
            length = unpack('Q')
            if length > file_size:
                raise ValueError('Повреждённая строка GGUF')
            if keep:
                if length > 1024*1024:
                    raise ValueError('Слишком длинная строка метаданных GGUF')
                return src.read(length).decode('utf-8')
            src.seek(length, 1)
        def value(typ, keep=True):
            if typ in formats:
                return unpack(formats[typ])
            if typ == 8:
                return string(keep)
            if typ == 9:
                subtype, count = unpack('I'), unpack('Q')
                if count > 10_000_000 or subtype == 9:
                    raise ValueError('Некорректный массив GGUF')
                if subtype in formats:
                    src.seek(count*struct.calcsize(formats[subtype]), 1)
                else:
                    for _ in range(count):
                        value(subtype, False)
                return None
            raise ValueError('Неизвестный тип GGUF')
        if src.read(4) != b'GGUF' or unpack('I') not in (2,3):
            raise ValueError('Ожидается GGUF версии 2 или 3')
        unpack('Q')
        count = unpack('Q')
        if count > 100_000:
            raise ValueError('Слишком много метаданных GGUF')
        result = {}
        for _ in range(count):
            key, typ = string(), unpack('I')
            keep = not key.startswith('tokenizer.')
            val = value(typ, keep)
            if keep and val is not None:
                result[key] = val
        if src.tell() > file_size:
            raise ValueError('Обрезанный GGUF')
        return result

