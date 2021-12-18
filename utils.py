import os, requests, datetime
from PIL import Image
from io import BytesIO
from .paths import PATHS

TEMP_DIR = PATHS['temp']


def image_filename(header='MultiBot', post='.jpg'):
    return datetime.datetime.now().strftime('{}_image_%Y%m%d-%H%M%S{}'.format(header, post))


def format_filename(header='MultiBot', type='image', post='.txt'):
    return datetime.datetime.now().strftime(f'{header}_{type}_%Y%m%d-%H%M%S{post}')


def image_url_to_path(url, header='MultiBot', filename=None):
    resp = requests.get(url)
    image = Image.open(BytesIO(resp.content))
    if filename is None:
        filename = image_filename(header=header)
    abs_dir = TEMP_DIR
    abs_path = os.path.join(abs_dir, filename)
    try:
        os.mkdir(abs_dir)
    except FileExistsError:
        pass
    if image.mode == "P":
        image = image.convert('RGB')
    image.save(abs_path)
    return abs_path
