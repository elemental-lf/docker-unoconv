import os
import subprocess
from collections import namedtuple
from io import BytesIO, SEEK_SET
from typing import ByteString, List, Optional, Tuple, BinaryIO

from PIL import Image
from fs import open_fs
from celery import Celery
from fs.errors import ResourceNotFound

app = Celery('unoconv')
app.config_from_object('unoconv.celeryconfig')

_ImportFormat = namedtuple('ImportFormat', ['mime_type', 'document_type', 'import_filter', 'extension'])
_Dimensions = namedtuple(
    'Dimensions', ['pixel_height', 'pixel_width', 'logical_height', 'logical_width', 'scale_height', 'scale_width'])
_null_dimensions = _Dimensions(None, None, None, None, False, False)

# yapf: disable
FORMATS = [
    _ImportFormat(mime_type='application/vnd.oasis.opendocument.graphics', document_type='presentation', import_filter='odg', extension='.odg'),
    _ImportFormat(mime_type='application/vnd.oasis.opendocument.graphics-template', document_type='graphics', import_filter='otg', extension='.otg'),
    _ImportFormat(mime_type='application/vnd.oasis.opendocument.graphics-flat-xml', document_type='graphics', import_filter='fodg', extension='.fodg'),
    _ImportFormat(mime_type='application/vnd.oasis.opendocument.presentation', document_type='presentation', import_filter='odp', extension='.odp'),
    _ImportFormat(mime_type='application/vnd.oasis.opendocument.presentation-template', document_type='presentation', import_filter='otp', extension='.otp'),
    _ImportFormat(mime_type='application/vnd.oasis.opendocument.presentation-flat-xml', document_type='presentation', import_filter='fodp', extension='.fodp'),
    _ImportFormat(mime_type='application/vnd.oasis.opendocument.spreadsheet', document_type='spreadsheet', import_filter='ods', extension='.ods'),
    _ImportFormat(mime_type='application/vnd.oasis.opendocument.spreadsheet-template', document_type='spreadsheet', import_filter='ots', extension='.ots'),
    _ImportFormat(mime_type='application/vnd.oasis.opendocument.spreadsheet-flat-xml', document_type='spreadsheet', import_filter='fods', extension='.fods'),
    _ImportFormat(mime_type='application/vnd.oasis.opendocument.text', document_type='document', import_filter='odt', extension='.odt'),
    _ImportFormat(mime_type='application/vnd.oasis.opendocument.text-flat-xml', document_type='document', import_filter='fodt', extension='.fodt'),
    _ImportFormat(mime_type='application/vnd.oasis.opendocument.text-template', document_type='document', import_filter='ott', extension='.ott'),
    _ImportFormat(mime_type='application/vnd.oasis.opendocument.text-master-template', document_type='global', import_filter='otm', extension='.otm'),
    _ImportFormat(mime_type='application/vnd.sun.xml.calc', document_type='spreadsheet', import_filter='sxc', extension='.sxc'),
    _ImportFormat(mime_type='application/vnd.sun.xml.calc.template', document_type='spreadsheet', import_filter='stc', extension='.stc'),
    _ImportFormat(mime_type='application/vnd.sun.xml.draw', document_type='graphics', import_filter='sxd', extension='.sxd'),
    _ImportFormat(mime_type='application/vnd.sun.xml.draw.template', document_type='graphics', import_filter='std', extension='.std'),
    _ImportFormat(mime_type='application/vnd.sun.xml.impress', document_type='presentation', import_filter='sxi', extension='.sxi'),
    _ImportFormat(mime_type='application/vnd.sun.xml.impress.template', document_type='presentation', import_filter='sti', extension='.sti'),
    _ImportFormat(mime_type='application/vnd.sun.xml.math', document_type='formula', import_filter='sxm', extension='.sxm'),
    _ImportFormat(mime_type='application/vnd.sun.xml.writer', document_type='document', import_filter='sxw', extension='.sxw'),
    _ImportFormat(mime_type='application/vnd.sun.xml.writer.global', document_type='document', import_filter='sxg', extension='.sxg'),
    _ImportFormat(mime_type='application/vnd.sun.xml.writer.template', document_type='document', import_filter='stw', extension='.stw'),
    _ImportFormat(mime_type='application/vnd.sun.xml.writer.web', document_type='document', import_filter='stw', extension='.stw'),
    _ImportFormat(mime_type='application/msword', document_type='document', import_filter='doc', extension='.doc'),
    _ImportFormat(mime_type='application/msword', document_type='document', import_filter='doc', extension='.dot'),
    _ImportFormat(mime_type='application/x-mswrite', document_type='document', import_filter=None, extension='.wri'),
    _ImportFormat(mime_type='application/vnd.ms-works', document_type='document', import_filter=None, extension='.wps'),
    _ImportFormat(mime_type='application/vnd.ms-word.document.macroEnabled.12', document_type='document', import_filter=None, extension='.docm'),
    _ImportFormat(mime_type='application/vnd.ms-word.template.macroEnabled.12', document_type='document', import_filter='dotm', extension='.dotm'),
    _ImportFormat(mime_type='application/vnd.ms-powerpoint', document_type='presentation', import_filter='ppt', extension='.ppt'),
    _ImportFormat(mime_type='application/vnd.ms-powerpoint.presentation.macroEnabled.12', document_type='presentation', import_filter=None, extension='.pptm'),
    _ImportFormat(mime_type='application/vnd.ms-powerpoint', document_type='presentation', import_filter='pps', extension='.pps'),
    _ImportFormat(mime_type='application/vnd.ms-powerpoint.slideshow.macroEnabled.12', document_type='presentation', import_filter='pps', extension='.ppsm'),
    _ImportFormat(mime_type='application/vnd.ms-excel', document_type='spreadsheet', import_filter='xls', extension='.xls'),
    _ImportFormat(mime_type='application/vnd.ms-excel.sheet.macroEnabled.12', document_type='spreadsheet', import_filter='xls', extension='.xlsm'),
    _ImportFormat(mime_type='application/vnd.ms-excel', document_type='spreadsheet', import_filter='xlt', extension='.xlt'),
    _ImportFormat(mime_type='application/vnd.ms-excel.sheet.macroEnabled.12', document_type='spreadsheet', import_filter='xltm', extension='.xltm'),
    _ImportFormat(mime_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', document_type='spreadsheet', import_filter='xlsx', extension='.xlsx'),
    _ImportFormat(mime_type='application/vnd.openxmlformats-officedocument.spreadsheetml.template', document_type='spreadsheet', import_filter='xlsx', extension='.xlsx'),
    _ImportFormat(mime_type='application/vnd.openxmlformats-officedocument.presentationml.presentation', document_type='presentation', import_filter='pptx', extension='.pptx'),
    _ImportFormat(mime_type='application/vnd.openxmlformats-officedocument.presentationml.template', document_type='presentation', import_filter='pptx', extension='.pptx'),
    _ImportFormat(mime_type='application/vnd.openxmlformats-officedocument.presentationml.slideshow', document_type='presentation', import_filter='pptx', extension='.pptx'),
    _ImportFormat(mime_type='application/vnd.openxmlformats-officedocument.presentationml.slide', document_type='presentation', import_filter='pptx', extension='.pptx'),
    _ImportFormat(mime_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document', document_type='document', import_filter='docx', extension='.docx'),
    _ImportFormat(mime_type='application/vnd.openxmlformats-officedocument.wordprocessingml.template', document_type='document', import_filter='docx', extension='.dotx'),
    _ImportFormat(mime_type='application/wps-office.doc', document_type='document', import_filter='doc', extension='.doc'),
    _ImportFormat(mime_type='application/wps-office.docx', document_type='document', import_filter='docx', extension='.docx'),
    _ImportFormat(mime_type='application/wps-office.xls', document_type='spreadsheet', import_filter='xls', extension='.xls'),
    _ImportFormat(mime_type='application/wps-office.xlsx', document_type='spreadsheet', import_filter='xlsx', extension='.xlsx'),
    _ImportFormat(mime_type='application/wps-office.ppt', document_type='presentation', import_filter='ppt', extension='.ppt'),
    _ImportFormat(mime_type='application/wps-office.pptx', document_type='presentation', import_filter='pptx', extension='.pptx'),
    _ImportFormat(mime_type='application/docbook+xml', document_type='document', import_filter='docbook', extension='.docbook'),
    _ImportFormat(mime_type='text/csv', document_type='spreadsheet', import_filter='csv', extension='.csv'),
    _ImportFormat(mime_type='text/spreadsheet', document_type='spreadsheet', import_filter='slk', extension='.slk'),
    _ImportFormat(mime_type='application/vnd.stardivision.draw', document_type='graphics', import_filter='sda', extension='.sda'),
    _ImportFormat(mime_type='application/vnd.stardivision.calc', document_type='spreadsheet', import_filter='sdc', extension='.sdc'),
    _ImportFormat(mime_type='application/vnd.sun.xml.calc.template', document_type='spreadsheet', import_filter='stc', extension='.stc'),
    _ImportFormat(mime_type='application/vnd.stardivision.impress', document_type='presentation', import_filter='sdd', extension='.sdd'),
    _ImportFormat(mime_type='application/vnd.stardivision.writer', document_type='document', import_filter='sdw', extension='.sdw'),
    _ImportFormat(mime_type='application/x-starwriter', document_type='document', import_filter='sdw', extension='.sdw'),
    _ImportFormat(mime_type='image/tiff', document_type='graphics', import_filter='tiff', extension='.tiff'),
    _ImportFormat(mime_type='image/tiff', document_type='graphics', import_filter='tiff', extension='.tif'),
    _ImportFormat(mime_type='image/emf', document_type='graphics', import_filter='emf', extension='.emf'),
    _ImportFormat(mime_type='image/x-emf', document_type='graphics', import_filter='emf', extension='.emf'),
    _ImportFormat(mime_type='image/x-svm', document_type='graphics', import_filter='svm', extension='.svm'),
    _ImportFormat(mime_type='image/wmf', document_type='graphics', import_filter='wmf', extension='.wmf'),
    _ImportFormat(mime_type='image/x-wmf', document_type='graphics', import_filter='wmf', extension='.wmf'),
    _ImportFormat(mime_type='image/x-pict', document_type='graphics', import_filter='pct', extension='.pct'),
    _ImportFormat(mime_type='image/x-cmx', document_type='graphics', import_filter='cmx', extension='.cmx'),
    _ImportFormat(mime_type='image/svg+xml', document_type='graphics', import_filter='svg', extension='.svg'),
    _ImportFormat(mime_type='image/bmp', document_type='graphics', import_filter='bmp', extension='.bmp'),
    _ImportFormat(mime_type='image/x-ms-bmp', document_type='graphics', import_filter='bmp', extension='.bmp'),
    _ImportFormat(mime_type='image/x-eps', document_type='graphics', import_filter='eps', extension='.eps'),
]
# yapf: enable

UNOCONV_DEFAULT_TIMEOUT = 300


def _determine_import_format(mime_type: str, extension: str) -> Optional[_ImportFormat]:
    # Search for a full match
    if mime_type is not None and extension is not None and extension not in ['.', '']:
        for import_format in FORMATS:
            if mime_type == import_format.mime_type and extension == import_format.extension:
                return import_format
    # Search only by extension
    if extension is not None and extension not in ['.', '']:
        for import_format in FORMATS:
            if extension == import_format.extension:
                return import_format
    # Search only by MIME type
    if mime_type is not None:
        for import_format in FORMATS:
            if mime_type == import_format.mime_type:
                return import_format
    return None


@app.task
def supported_import_format(*, mime_type: str = None, extension: str = None) -> bool:
    import_format = _determine_import_format(mime_type, extension)
    return import_format is not None


def _call_unoconv(*, args: List[str], data: BinaryIO, timeout: int) -> BytesIO:
    args.insert(0, 'unoconv')
    args.extend(['--stdin', '--stdout', '--timeout', str(timeout)])

    try:
        # Unfortunately we can't pass the file like object directly to subprocess.run as it requires a real
        # OS file descriptor underneath.
        result = subprocess.run(
            args, input=data.read(), stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=timeout)
    except subprocess.CalledProcessError as exception:
        raise RuntimeError(f'unoconv invocation failed with return code {result.returncode} and output: ' +
                           exception.stderr.decode('utf-8', errors='ignore').replace('\n', ', ')) from None
    except subprocess.TimeoutExpired as exception:
        raise RuntimeError(f'unoconv invocation failed due to timeout with output: ' +
                           exception.stderr.decode('utf-8', errors='ignore').replace('\n', ', ')) from None
    except Exception as exception:
        raise RuntimeError(f'unoconv invocation failed with a {type(exception).__name__} exception: {str(exception)}.') from None

    decoded_stderr = result.stderr.decode('utf-8', errors='ignore').replace('\n', ', ')
    if result.returncode == 0:
        if len(result.stdout) == 0:
            raise RuntimeError(f'unoconv invocation was successful but did not return any data. Output on stderr was: ' + decoded_stderr)
        return BytesIO(result.stdout)
    else:
        raise RuntimeError(f'unoconv invocation failed with return code {result.returncode} and output: ' + decoded_stderr)


def _populate_args_for_image(*, import_format: _ImportFormat, export_format_name: str,
                             dimensions: _Dimensions) -> List[str]:
    unoconv_args = ['--format', export_format_name]
    if import_format.document_type is not None:
        unoconv_args.extend(['--doctype', import_format.document_type])
    if import_format.import_filter is not None:
        unoconv_args.extend(['--import-filter-name', import_format.import_filter])

    if dimensions.pixel_height:
        unoconv_args.extend(['-e', f'PixelHeight={dimensions.pixel_height}'])
    if dimensions.pixel_width:
        unoconv_args.extend(['-e', f'PixelWidth={dimensions.pixel_width}'])

    if dimensions.logical_height:
        unoconv_args.extend(['-e', f'LogicalHeight={dimensions.logical_height}'])
    if dimensions.logical_width:
        unoconv_args.extend(['-e', f'LogicalWidth={dimensions.logical_width}'])

    return unoconv_args


def _scale_dimensions(*, data: BinaryIO, dimensions: _Dimensions) -> _Dimensions:

    assert dimensions.scale_height or dimensions.scale_width

    try:
        image = Image.open(data)
        image.load()
    except Exception as exception:
        raise RuntimeError(f'Loading internal image data failed with a {type(exception).__name__} exception: {str(exception)}.') from None

    if dimensions.scale_height:
        scaled_pixel_height = round(dimensions.pixel_width * image.height / image.width)
        scaled_pixel_width = dimensions.pixel_width

        if dimensions.logical_width is not None:
            scaled_logical_height = round(dimensions.logical_width * image.height / image.width)
        else:
            scaled_logical_height = dimensions.logical_height
        scaled_logical_width = dimensions.logical_width
    elif dimensions.scale_width:
        scaled_pixel_height = dimensions.pixel_height
        scaled_pixel_width = round(dimensions.pixel_height * image.width / image.height)

        scaled_logical_height = dimensions.logical_height
        if dimensions.logical_height is not None:
            scaled_logical_width = round(dimensions.logical_height * image.width / image.height)
        else:
            scaled_logical_width = dimensions.logical_width

    return _Dimensions(
        pixel_height=scaled_pixel_height,
        pixel_width=scaled_pixel_width,
        logical_height=scaled_logical_height,
        logical_width=scaled_logical_width,
        scale_height=dimensions.scale_height,
        scale_width=dimensions.scale_width)


def _convert_to_jpg(*, data: BinaryIO, import_format: _ImportFormat, dimensions: _Dimensions, quality: int,
                    timeout: int) -> BytesIO:

    if dimensions.scale_height or dimensions.scale_width:
        unoconv_args = _populate_args_for_image(
            import_format=import_format, export_format_name='jpg', dimensions=_null_dimensions)
        unoconv_args.extend(['-e', f'Quality=1'])

        image = _call_unoconv(args=unoconv_args, data=data, timeout=timeout)
        dimensions = _scale_dimensions(data=image, dimensions=dimensions)

    unoconv_args = _populate_args_for_image(
        import_format=import_format, export_format_name='jpg', dimensions=dimensions)
    if quality is not None:
        unoconv_args.extend(['-e', f'Quality={quality}'])

    data.seek(0, SEEK_SET)
    return _call_unoconv(args=unoconv_args, data=data, timeout=timeout)


def _convert_to_png(*, data: BinaryIO, import_format: _ImportFormat, dimensions: _Dimensions, compression: int,
                    timeout: int) -> BytesIO:

    if dimensions.scale_height or dimensions.scale_width:
        unoconv_args = _populate_args_for_image(
            import_format=import_format, export_format_name='png', dimensions=_null_dimensions)
        unoconv_args.extend(['-e', f'Compression=1'])

        image_io = _call_unoconv(args=unoconv_args, data=data, timeout=timeout)
        dimensions = _scale_dimensions(data=image_io, dimensions=dimensions)

    unoconv_args = _populate_args_for_image(
        import_format=import_format, export_format_name='png', dimensions=dimensions)
    if compression is not None:
        unoconv_args.extend(['-e', f'Compression={compression}'])

    data.seek(0, SEEK_SET)
    return _call_unoconv(args=unoconv_args, data=data, timeout=timeout)


def _convert_to_pdf(*, data: BinaryIO, import_format: _ImportFormat, paper_format: str, paper_orientation: str,
                    timeout: int) -> BytesIO:
    unoconv_args = ['--format', 'pdf']
    if import_format.document_type is not None:
        unoconv_args.extend(['--doctype', import_format.document_type])
    if import_format.import_filter is not None:
        unoconv_args.extend(['--import-filter-name', import_format.import_filter])
    if paper_format is not None:
        unoconv_args.extend(['-P', f'PaperFormat={paper_format}'])
    if paper_orientation is not None:
        unoconv_args.extend(['-P', f'PaperOrientation={paper_orientation}'])

    return _call_unoconv(args=unoconv_args, data=data, timeout=timeout)


def _read_data(*, fs_url: str, file: str, mime_type: str, extension: str) -> Tuple[_ImportFormat, BytesIO]:
    try:
        with open_fs(fs_url) as fs:
            data = BytesIO(fs.readbytes(file))
    except ResourceNotFound:
        raise FileNotFoundError(f'Input file {file} not found.')
    except Exception as exception:
        raise RuntimeError(f'Reading file failed with a {type(exception).__name__} exception: {str(exception)}.') from None

    if extension is None:
        _, determined_extension = os.path.splitext(file)
    else:
        determined_extension = extension

    import_format = _determine_import_format(mime_type, determined_extension)
    if import_format is None:
        raise ValueError('Unsupported input document type.')

    return import_format, data


def _write_data(*, fs_url: str, file: str, data: BinaryIO) -> None:
    try:
        with open_fs(fs_url) as fs:
            fs.writebytes(file, data.read())
    except Exception as exception:
        raise RuntimeError(f'Writing file failed with a {type(exception).__name__} exception: {str(exception)}.') from None


def _build_dimensions(*, pixel_height: Optional[int], pixel_width: Optional[int], logical_height: Optional[int],
                      logical_width: Optional[int], scale_height: bool, scale_width: bool) -> _Dimensions:
    if scale_height and scale_width:
        raise ValueError('Scaling in both dimensions is not supported.')

    if scale_height and pixel_width is None:
        raise ValueError('When scaling the height the pixel width must be specified.')
    elif scale_width and pixel_height is None:
        raise ValueError('When scaling the width the pixel height must be specified.')
    elif not scale_height and not scale_width and (pixel_height is None and pixel_width is not None or
                                                   pixel_height is not None and pixel_width is None):
        raise ValueError('Both pixel height and width must be set or unset.')

    if pixel_height is not None and pixel_height < 0:
        raise ValueError('The pixel height must be a positive integer.')
    if pixel_width is not None and pixel_width < 0:
        raise ValueError('The pixel width must be a positive integer.')
    if logical_height is not None and logical_height < 0:
        raise ValueError('The logical height must be a positive integer.')
    if logical_width is not None and logical_width < 0:
        raise ValueError('The logical width must be a positive integer.')

    return _Dimensions(
        pixel_height=pixel_height,
        pixel_width=pixel_width,
        logical_height=logical_height,
        logical_width=logical_width,
        scale_height=scale_height,
        scale_width=scale_width)


@app.task
def generate_preview_jpg(*,
                         input_fs_url: str,
                         input_file: str,
                         output_fs_url: str,
                         output_file: str,
                         mime_type: str = None,
                         extension: str = None,
                         pixel_height: int = None,
                         pixel_width: int = None,
                         logical_height: int = None,
                         logical_width: int = None,
                         scale_height: bool = False,
                         scale_width: bool = False,
                         quality: int = None,
                         timeout: int = UNOCONV_DEFAULT_TIMEOUT):
    dimensions = _build_dimensions(
        pixel_height=pixel_height,
        pixel_width=pixel_width,
        logical_height=logical_height,
        logical_width=logical_width,
        scale_height=scale_height,
        scale_width=scale_width)
    if quality is not None and (quality < 1 or quality > 100):
        raise ValueError('JPEG quality must be in the range of 1 to 100 (inclusive).')

    import_format, data = _read_data(fs_url=input_fs_url, file=input_file, mime_type=mime_type, extension=extension)
    output_data = _convert_to_jpg(
        data=data, import_format=import_format, dimensions=dimensions, quality=quality, timeout=timeout)
    _write_data(fs_url=output_fs_url, file=output_file, data=output_data)


@app.task
def generate_preview_png(*,
                         input_fs_url: str,
                         input_file: str,
                         output_fs_url: str,
                         output_file: str,
                         mime_type: str = None,
                         extension: str = None,
                         pixel_height: int = None,
                         pixel_width: int = None,
                         logical_height: int = None,
                         logical_width: int = None,
                         scale_height: bool = False,
                         scale_width: bool = False,
                         compression: int = None,
                         timeout: int = UNOCONV_DEFAULT_TIMEOUT):
    dimensions = _build_dimensions(
        pixel_height=pixel_height,
        pixel_width=pixel_width,
        logical_height=logical_height,
        logical_width=logical_width,
        scale_height=scale_height,
        scale_width=scale_width)
    if compression is not None and (compression < 1 or compression > 9):
        raise ValueError('PNG compression must be in the range of 1 to 9 (inclusive).')

    import_format, data = _read_data(fs_url=input_fs_url, file=input_file, mime_type=mime_type, extension=extension)
    output_data = _convert_to_png(
        data=data, import_format=import_format, dimensions=dimensions, compression=compression, timeout=timeout)
    _write_data(fs_url=output_fs_url, file=output_file, data=output_data)


@app.task
def generate_pdf(*,
                 input_fs_url: str,
                 input_file: str,
                 output_fs_url: str,
                 output_file: str,
                 mime_type: str = None,
                 extension: str = None,
                 paper_format: str = None,
                 paper_orientation: str = None,
                 timeout: int = UNOCONV_DEFAULT_TIMEOUT):
    import_format, data = _read_data(fs_url=input_fs_url, file=input_file, mime_type=mime_type, extension=extension)
    output_data = _convert_to_pdf(
        data=data,
        import_format=import_format,
        paper_format=paper_format,
        paper_orientation=paper_orientation,
        timeout=timeout)
    _write_data(fs_url=output_fs_url, file=output_file, data=output_data)
