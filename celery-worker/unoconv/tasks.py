import itertools
import os
import subprocess
from typing import ByteString, List, Optional, Tuple

from fs import open_fs
from celery import Celery
from fs.errors import ResourceNotFound

app = Celery('unoconv')
app.config_from_object('unoconv.celeryconfig')


class ImportFormat:

    id_counter = itertools.count(start=1)

    def __init__(self, *, mime_type: str, document_type: str, import_filter: str, extension: str):
        self.mime_type = mime_type
        self.document_type = document_type
        self.import_filter = import_filter
        self.extension = extension
        self.id = next(self.id_counter)


# yapf: disable
FORMATS = [
    ImportFormat(mime_type='application/vnd.oasis.opendocument.graphics', document_type='presentation', import_filter='odg', extension='.odg'),
    ImportFormat(mime_type='application/vnd.oasis.opendocument.graphics-template', document_type='graphics', import_filter='otg', extension='.otg'),
    ImportFormat(mime_type='application/vnd.oasis.opendocument.graphics-flat-xml', document_type='graphics', import_filter='fodg', extension='.fodg'),
    ImportFormat(mime_type='application/vnd.oasis.opendocument.presentation', document_type='presentation', import_filter='odp', extension='.odp'),
    ImportFormat(mime_type='application/vnd.oasis.opendocument.presentation-template', document_type='presentation', import_filter='otp', extension='.otp'),
    ImportFormat(mime_type='application/vnd.oasis.opendocument.presentation-flat-xml', document_type='presentation', import_filter='fodp', extension='.fodp'),
    ImportFormat(mime_type='application/vnd.oasis.opendocument.spreadsheet', document_type='spreadsheet', import_filter='ods', extension='.ods'),
    ImportFormat(mime_type='application/vnd.oasis.opendocument.spreadsheet-template', document_type='spreadsheet', import_filter='ots', extension='.ots'),
    ImportFormat(mime_type='application/vnd.oasis.opendocument.spreadsheet-flat-xml', document_type='spreadsheet', import_filter='fods', extension='.fods'),
    ImportFormat(mime_type='application/vnd.oasis.opendocument.text', document_type='document', import_filter='odt', extension='.odt'),
    ImportFormat(mime_type='application/vnd.oasis.opendocument.text-flat-xml', document_type='document', import_filter='fodt', extension='.fodt'),
    ImportFormat(mime_type='application/vnd.oasis.opendocument.text-template', document_type='document', import_filter='ott', extension='.ott'),
    ImportFormat(mime_type='application/vnd.oasis.opendocument.text-master-template', document_type='global', import_filter='otm', extension='.otm'),
    ImportFormat(mime_type='application/vnd.sun.xml.calc', document_type='spreadsheet', import_filter='sxc', extension='.sxc'),
    ImportFormat(mime_type='application/vnd.sun.xml.calc.template', document_type='spreadsheet', import_filter='stc', extension='.stc'),
    ImportFormat(mime_type='application/vnd.sun.xml.draw', document_type='graphics', import_filter='sxd', extension='.sxd'),
    ImportFormat(mime_type='application/vnd.sun.xml.draw.template', document_type='graphics', import_filter='std', extension='.std'),
    ImportFormat(mime_type='application/vnd.sun.xml.impress', document_type='presentation', import_filter='sxi', extension='.sxi'),
    ImportFormat(mime_type='application/vnd.sun.xml.impress.template', document_type='presentation', import_filter='sti', extension='.sti'),
    ImportFormat(mime_type='application/vnd.sun.xml.math', document_type='formula', import_filter='sxm', extension='.sxm'),
    ImportFormat(mime_type='application/vnd.sun.xml.writer', document_type='document', import_filter='sxw', extension='.sxw'),
    ImportFormat(mime_type='application/vnd.sun.xml.writer.global', document_type='document', import_filter='sxg', extension='.sxg'),
    ImportFormat(mime_type='application/vnd.sun.xml.writer.template', document_type='document', import_filter='stw', extension='.stw'),
    ImportFormat(mime_type='application/vnd.sun.xml.writer.web', document_type='document', import_filter='stw', extension='.stw'),
    ImportFormat(mime_type='application/msword', document_type='document', import_filter='doc', extension='.doc'),
    ImportFormat(mime_type='application/msword', document_type='document', import_filter='doc', extension='.dot'),
    ImportFormat(mime_type='application/x-mswrite', document_type='document', import_filter=None, extension='.wri'),
    ImportFormat(mime_type='application/vnd.ms-works', document_type='document', import_filter=None, extension='.wps'),
    ImportFormat(mime_type='application/vnd.ms-word.document.macroEnabled.12', document_type='document', import_filter=None, extension='.docm'),
    ImportFormat(mime_type='application/vnd.ms-word.template.macroEnabled.12', document_type='document', import_filter='dotm', extension='.dotm'),
    ImportFormat(mime_type='application/vnd.ms-powerpoint', document_type='presentation', import_filter='ppt', extension='.ppt'),
    ImportFormat(mime_type='application/vnd.ms-powerpoint.presentation.macroEnabled.12', document_type='presentation', import_filter=None, extension='.pptm'),
    ImportFormat(mime_type='application/vnd.ms-powerpoint', document_type='presentation', import_filter='pps', extension='.pps'),
    ImportFormat(mime_type='application/vnd.ms-powerpoint.slideshow.macroEnabled.12', document_type='presentation', import_filter='pps', extension='.ppsm'),
    ImportFormat(mime_type='application/vnd.ms-excel', document_type='spreadsheet', import_filter='xls', extension='.xls'),
    ImportFormat(mime_type='application/vnd.ms-excel.sheet.macroEnabled.12', document_type='spreadsheet', import_filter='xls', extension='.xlsm'),
    ImportFormat(mime_type='application/vnd.ms-excel', document_type='spreadsheet', import_filter='xlt', extension='.xlt'),
    ImportFormat(mime_type='application/vnd.ms-excel.sheet.macroEnabled.12', document_type='spreadsheet', import_filter='xltm', extension='.xltm'),
    ImportFormat(mime_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', document_type='spreadsheet', import_filter='xlsx', extension='.xlsx'),
    ImportFormat(mime_type='application/vnd.openxmlformats-officedocument.spreadsheetml.template', document_type='spreadsheet', import_filter='xlsx', extension='.xlsx'),
    ImportFormat(mime_type='application/vnd.openxmlformats-officedocument.presentationml.presentation', document_type='presentation', import_filter='pptx', extension='.pptx'),
    ImportFormat(mime_type='application/vnd.openxmlformats-officedocument.presentationml.template', document_type='presentation', import_filter='pptx', extension='.pptx'),
    ImportFormat(mime_type='application/vnd.openxmlformats-officedocument.presentationml.slideshow', document_type='presentation', import_filter='pptx', extension='.pptx'),
    ImportFormat(mime_type='application/vnd.openxmlformats-officedocument.presentationml.slide', document_type='presentation', import_filter='pptx', extension='.pptx'),
    ImportFormat(mime_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document', document_type='document', import_filter='docx', extension='.docx'),
    ImportFormat(mime_type='application/vnd.openxmlformats-officedocument.wordprocessingml.template', document_type='document', import_filter='docx', extension='.dotx'),
    ImportFormat(mime_type='application/wps-office.doc', document_type='document', import_filter='doc', extension='.doc'),
    ImportFormat(mime_type='application/wps-office.docx', document_type='document', import_filter='docx', extension='.docx'),
    ImportFormat(mime_type='application/wps-office.xls', document_type='spreadsheet', import_filter='xls', extension='.xls'),
    ImportFormat(mime_type='application/wps-office.xlsx', document_type='spreadsheet', import_filter='xlsx', extension='.xlsx'),
    ImportFormat(mime_type='application/wps-office.ppt', document_type='presentation', import_filter='ppt', extension='.ppt'),
    ImportFormat(mime_type='application/wps-office.pptx', document_type='presentation', import_filter='pptx', extension='.pptx'),
    ImportFormat(mime_type='application/docbook+xml', document_type='document', import_filter='docbook', extension='.docbook'),
    ImportFormat(mime_type='text/csv', document_type='spreadsheet', import_filter='csv', extension='.csv'),
    ImportFormat(mime_type='text/spreadsheet', document_type='spreadsheet', import_filter='slk', extension='.slk'),
    ImportFormat(mime_type='application/vnd.stardivision.draw', document_type='graphics', import_filter='sda', extension='.sda'),
    ImportFormat(mime_type='application/vnd.stardivision.calc', document_type='spreadsheet', import_filter='sdc', extension='.sdc'),
    ImportFormat(mime_type='application/vnd.sun.xml.calc.template', document_type='spreadsheet', import_filter='stc', extension='.stc'),
    ImportFormat(mime_type='application/vnd.stardivision.impress', document_type='presentation', import_filter='sdd', extension='.sdd'),
    ImportFormat(mime_type='application/vnd.stardivision.writer', document_type='document', import_filter='sdw', extension='.sdw'),
    ImportFormat(mime_type='application/x-starwriter', document_type='document', import_filter='sdw', extension='.sdw'),
    ImportFormat(mime_type='image/tiff', document_type='graphics', import_filter='tiff', extension='.tiff'),
    ImportFormat(mime_type='image/tiff', document_type='graphics', import_filter='tiff', extension='.tif'),
    ImportFormat(mime_type='image/emf', document_type='graphics', import_filter='emf', extension='.emf'),
    ImportFormat(mime_type='image/x-emf', document_type='graphics', import_filter='emf', extension='.emf'),
    ImportFormat(mime_type='image/x-svm', document_type='graphics', import_filter='svm', extension='.svm'),
    ImportFormat(mime_type='image/wmf', document_type='graphics', import_filter='wmf', extension='.wmf'),
    ImportFormat(mime_type='image/x-wmf', document_type='graphics', import_filter='wmf', extension='.wmf'),
    ImportFormat(mime_type='image/x-pict', document_type='graphics', import_filter='pct', extension='.pct'),
    ImportFormat(mime_type='image/x-cmx', document_type='graphics', import_filter='cmx', extension='.cmx'),
    ImportFormat(mime_type='image/svg+xml', document_type='graphics', import_filter='svg', extension='.svg'),
    ImportFormat(mime_type='image/bmp', document_type='graphics', import_filter='bmp', extension='.bmp'),
    ImportFormat(mime_type='image/x-ms-bmp', document_type='graphics', import_filter='bmp', extension='.bmp'),
    ImportFormat(mime_type='image/x-eps', document_type='graphics', import_filter='eps', extension='.eps'),
]
# yapf: enable

UNOCONV_DEFAULT_TIMEOUT = 300


def _determine_import_format(mime_type: str, extension: str) -> Optional[ImportFormat]:
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


def _call_unoconv(args: List[str], data: ByteString, timeout: int) -> bytes:
    args.insert(0, 'unoconv')
    args.extend(['--stdin', '--stdout', '--timeout', str(timeout)])

    try:
        result = subprocess.run(args, input=data, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=timeout)
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
        return result.stdout
    else:
        raise RuntimeError(f'unoconv invocation failed with return code {result.returncode} and output: ' + decoded_stderr)


def _convert_to_image(data: ByteString, import_format: ImportFormat, export_format_name: str, height: int, width: int,
                      timeout: int) -> bytes:
    unoconv_args = ['--format', export_format_name]
    if import_format.document_type is not None:
        unoconv_args.extend(['--doctype', import_format.document_type])
    if import_format.import_filter is not None:
        unoconv_args.extend(['--import-filter-name', import_format.import_filter])

    if height:
        unoconv_args.extend(['-e', f'PixelHeight={height}'])
        unoconv_args.extend(['-e', f'PixelWidth={width}'])

    return _call_unoconv(unoconv_args, data, timeout)


def _convert_to_pdf(data: ByteString, import_format: ImportFormat, timeout: int):
    unoconv_args = ['--format', 'pdf']
    if import_format.document_type is not None:
        unoconv_args.extend(['--doctype', import_format.document_type])
    if import_format.import_filter is not None:
        unoconv_args.extend(['--import-filter-name', import_format.import_filter])

    return _call_unoconv(unoconv_args, data, timeout)


def _read_data(fs_url: str, file: str, mime_type: str, extension: str) -> Tuple[ImportFormat, bytes]:
    try:
        with open_fs(fs_url) as fs:
            # Unfortunately we can't pass the file like object directly to subprocess.run as it requires a real
            # OS file descriptor underneath.
            data = fs.readbytes(file)
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


def _write_data(fs_url: str, file: str, data: ByteString) -> None:
    try:
        with open_fs(fs_url) as fs:
            fs.writebytes(file, data)
    except Exception as exception:
        raise RuntimeError(f'Writing file failed with a {type(exception).__name__} exception: {str(exception)}.') from None


def _check_preview_dimensions(height: int, width: int) -> None:
    if height is None and width is not None or height is not None and width is None:
        raise ValueError('Both height and width must be set.')


@app.task
def generate_preview_jpg(*,
                         input_fs_url: str,
                         input_file: str,
                         output_fs_url: str,
                         output_file: str,
                         mime_type: str = None,
                         extension: str = None,
                         height: int = None,
                         width: int = None,
                         timeout: int = UNOCONV_DEFAULT_TIMEOUT):
    _check_preview_dimensions(height, width)
    import_format, data = _read_data(input_fs_url, input_file, mime_type, extension)
    output_data = _convert_to_image(data, import_format, 'jpg', height, width, timeout)
    _write_data(output_fs_url, output_file, output_data)


@app.task
def generate_preview_png(*,
                         input_fs_url: str,
                         input_file: str,
                         output_fs_url: str,
                         output_file: str,
                         mime_type: str = None,
                         extension: str = None,
                         height: int = None,
                         width: int = None,
                         timeout: int = UNOCONV_DEFAULT_TIMEOUT):
    _check_preview_dimensions(height, width)
    import_format, data = _read_data(input_fs_url, input_file, mime_type, extension)
    output_data = _convert_to_image(data, import_format, 'png', height, width, timeout)
    _write_data(output_fs_url, output_file, output_data)


@app.task
def generate_pdf(*,
                 input_fs_url: str,
                 input_file: str,
                 output_fs_url: str,
                 output_file: str,
                 mime_type: str = None,
                 extension: str = None,
                 timeout: int = UNOCONV_DEFAULT_TIMEOUT):
    import_format, data = _read_data(input_fs_url, input_file, mime_type, extension)
    output_data = _convert_to_pdf(data, import_format, timeout)
    _write_data(output_fs_url, output_file, output_data)
