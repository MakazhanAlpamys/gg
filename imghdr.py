# Эмуляция модуля imghdr для работы с python-telegram-bot на Python 3.13+

def what(file, h=None):
    """Определяет тип файла изображения.
    
    Возвращает тип файла изображения или None, если не может определить.
    Поддерживаемые типы: jpeg, png, gif, bmp, webp.
    """
    if h is None:
        if isinstance(file, str):
            with open(file, 'rb') as f:
                h = f.read(32)
        else:
            location = file.tell()
            h = file.read(32)
            file.seek(location)
    
    if h[:4] == b'\xff\xd8\xff\xe0' and h[6:11] == b'JFIF\0':
        return 'jpeg'
    elif h[:4] == b'\xff\xd8\xff\xe1' and h[6:11] == b'Exif\0':
        return 'jpeg'
    elif h[:4] == b'\x89PNG':
        return 'png'
    elif h[:6] == b'GIF87a' or h[:6] == b'GIF89a':
        return 'gif'
    elif h[:2] == b'BM':
        return 'bmp'
    elif h[:4] == b'RIFF' and h[8:12] == b'WEBP':
        return 'webp'
    else:
        return None

# Добавляем тесты на наиболее распространенные типы изображений
tests = []