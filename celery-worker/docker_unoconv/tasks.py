import itertools
import os
import subprocess
from contextlib import contextmanager
from copy import deepcopy
from io import BytesIO
from typing import BinaryIO, ByteString, Dict, List, Optional, Tuple

import boto3
from botocore.client import Config as BotoCoreClientConfig
from botocore.handlers import set_list_objects_encoding_type_url
from celery import Celery

app = Celery('docker_unoconv')
app.config_from_object('docker_unoconv.celeryconfig')


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


def _determine_input_format(mime_type: str, extension: str) -> Optional[ImportFormat]:
    # Search for a full match
    if mime_type is not None and extension is not None and extension not in ['.', '']:
        for input_format in FORMATS:
            if mime_type == input_format.mime_type and extension == input_format.extension:
                return input_format
    # Search only by extension
    if extension is not None and extension not in ['.', '']:
        for input_format in FORMATS:
            if extension == input_format.extension:
                return input_format
    # Search only by MIME type
    if mime_type is not None:
        for input_format in FORMATS:
            if mime_type == input_format.mime_type:
                return input_format
    return None


@app.task
def get_input_format(*, mime_type: str = None, extension: str = None) -> Optional[Tuple[str, str, str, str]]:
    input_format = _determine_input_format(mime_type, extension)
    if input_format is not None:
        return input_format.id, input_format.mime_type, input_format.document_type, input_format.import_filter, input_format.extension
    else:
        return None


@app.task
def supported_input_format(*, mime_type: str = None, extension: str = None) -> bool:
    input_format = _determine_input_format(mime_type, extension)
    return input_format is not None


@app.task
def get_input_formats() -> List[Tuple[str, str, str, str]]:
    input_formats = []
    for input_format in FORMATS:
        input_formats.append((input_format.id, input_format.mime_type, input_format.document_type,
                              input_format.import_filter, input_format.extension))
    return input_formats


def _call_unoconv(args: List[str], inputf: BinaryIO, timeout: int) -> bytes:
    args.insert(0, 'unoconv')
    args.extend(['--stdin', '--stdout', '--timeout', str(timeout)])

    try:
        result = subprocess.run(
            args, input=inputf.read(), stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=timeout)
    except subprocess.CalledProcessError as exception:
        raise RuntimeError(f'unoconv invocation failed with return code {result.returncode} and output: ' +
                           exception.stderr.decode('utf-8', errors='ignore').replace('\n', ', ')) from None
    except subprocess.TimeoutExpired as exception:
        raise RuntimeError(f'unoconv invocation failed due to timeout with output: ' +
                           exception.stderr.decode('utf-8', errors='ignore').replace('\n', ', ')) from None
    except Exception as exception:
        raise RuntimeError(f'unoconv invocation failed with a {type(exception).__name__} exception: {str(exception)}.') from None

    if result.returncode == 0:
        return result.stdout
    else:
        raise RuntimeError(f'unoconv invocation failed with return code {result.returncode} and output: ' +
                           result.stderr.decode('utf-8', errors='ignore').replace('\n', ', '))


def _convert_to_image(inputf: BinaryIO, input_format: ImportFormat, output_format_name: str, height: int, width: int,
                      timeout: int) -> bytes:
    unoconv_args = ['--format', output_format_name]
    if input_format.document_type is not None:
        unoconv_args.extend(['--doctype', input_format.document_type])
    if input_format.import_filter is not None:
        unoconv_args.extend(['--import-filter-name', input_format.import_filter])

    if height:
        unoconv_args.extend(['-e', f'PixelHeight={height}'])
        unoconv_args.extend(['-e', f'PixelWidth={width}'])

    return _call_unoconv(unoconv_args, inputf, timeout)


def _convert_to_pdf(inputf: BinaryIO, input_format: ImportFormat, timeout: int):
    unoconv_args = ['--format', 'pdf']
    if input_format.document_type is not None:
        unoconv_args.extend(['--doctype', input_format.document_type])
    if input_format.import_filter is not None:
        unoconv_args.extend(['--import-filter-name', input_format.import_filter])

    return _call_unoconv(unoconv_args, inputf, timeout)


#
# ByteString based tasks
#


@app.task
def generate_preview_jpg(*,
                         data: ByteString,
                         mime_type: str = None,
                         extension: str = None,
                         height: int = None,
                         width: int = None,
                         timeout: int = UNOCONV_DEFAULT_TIMEOUT):
    input_format = _determine_input_format(mime_type, extension)
    if input_format is None:
        raise ValueError('Unsupported input document type.')

    return _convert_to_image(BytesIO(data), input_format, 'jpg', height, width, timeout)


@app.task
def generate_preview_png(*,
                         data: ByteString,
                         mime_type: str = None,
                         extension: str = None,
                         height: int = None,
                         width: int = None,
                         timeout: int = UNOCONV_DEFAULT_TIMEOUT):
    input_format = _determine_input_format(mime_type, extension)
    if input_format is None:
        raise ValueError('Unsupported input document type.')

    return _convert_to_image(BytesIO(data), input_format, 'png', height, width, timeout)


@app.task
def generate_pdf(*,
                 data: ByteString,
                 mime_type: str = None,
                 extension: str = None,
                 timeout: int = UNOCONV_DEFAULT_TIMEOUT):
    input_format = _determine_input_format(mime_type, extension)
    if input_format is None:
        raise ValueError('Unsupported input document type.')

    return _convert_to_pdf(BytesIO(data), input_format, timeout)


#
# ByteString based tasks
#


@app.task
def generate_preview_jpg(*,
                         data: ByteString,
                         mime_type: str = None,
                         extension: str = None,
                         height: int = None,
                         width: int = None,
                         timeout: int = UNOCONV_DEFAULT_TIMEOUT):
    input_format = _determine_input_format(mime_type, extension)
    if input_format is None:
        raise ValueError('Unsupported input document type.')

    return _convert_to_image(BytesIO(data), input_format, 'jpg', height, width, timeout)


@app.task
def generate_preview_png(*,
                         data: ByteString,
                         mime_type: str = None,
                         extension: str = None,
                         height: int = None,
                         width: int = None,
                         timeout: int = UNOCONV_DEFAULT_TIMEOUT):
    input_format = _determine_input_format(mime_type, extension)
    if input_format is None:
        raise ValueError('Unsupported input document type.')

    return _convert_to_image(BytesIO(data), input_format, 'png', height, width, timeout)


@app.task
def generate_pdf(*,
                 data: ByteString,
                 mime_type: str = None,
                 extension: str = None,
                 timeout: int = UNOCONV_DEFAULT_TIMEOUT):
    input_format = _determine_input_format(mime_type, extension)
    if input_format is None:
        raise ValueError('Unsupported input document type.')

    return _convert_to_pdf(BytesIO(data), input_format, timeout)


#
# S3 based tasks
#


def _create_s3_resource(resource_config: Dict, disable_encoding_type: bool):
    my_resource_config = deepcopy(resource_config)
    if 'config' in my_resource_config:
        my_resource_config['config'] = BotoCoreClientConfig(**my_resource_config['config'])

    session = boto3.session.Session()
    if disable_encoding_type:
        session.events.unregister('before-parameter-build.s3.ListObjects', set_list_objects_encoding_type_url)

    return session.resource('s3', **my_resource_config)


@contextmanager
def _s3_object_stream(bucket: str, key: str, resource_config: Dict, disable_encoding_type: bool) -> BinaryIO:
    try:
        resource = _create_s3_resource(resource_config, disable_encoding_type)
    except Exception as exception:
        raise RuntimeError(f'S3 resource creation failed: {str(exception)}') from None

    try:
        stream = resource.Object(bucket, key).get()['Body']
        yield stream
    except Exception as exception:
        raise RuntimeError(f'S3 GET operation failed: {str(exception)}') from None
    finally:
        stream.close()


@app.task
def generate_preview_jpg_from_s3_object(*,
                                        bucket: str,
                                        key: str,
                                        mime_type: str = None,
                                        extension: str = None,
                                        height: int = None,
                                        width: int = None,
                                        resource_config: Dict,
                                        disable_encoding_type: bool = False,
                                        timeout: int = UNOCONV_DEFAULT_TIMEOUT):
    input_format = _determine_input_format(mime_type, extension)
    if input_format is None:
        raise ValueError('Unsupported input document type.')

    with _s3_object_stream(bucket, key, resource_config, disable_encoding_type) as inputf:
        return _convert_to_image(inputf, input_format, 'jpg', height, width, timeout)


@app.task
def generate_preview_png_from_s3_object(*,
                                        bucket: str,
                                        key: str,
                                        mime_type: str = None,
                                        extension: str = None,
                                        height: int = None,
                                        width: int = None,
                                        resource_config: Dict,
                                        disable_encoding_type: bool = False,
                                        timeout: int = UNOCONV_DEFAULT_TIMEOUT):
    input_format = _determine_input_format(mime_type, extension)
    if input_format is None:
        raise ValueError('Unsupported input document type.')

    with _s3_object_stream(bucket, key, resource_config, disable_encoding_type) as inputf:
        return _convert_to_image(inputf, input_format, 'png', height, width, timeout)


@app.task
def generate_pdf_from_s3_object(*,
                                bucket: str,
                                key: str,
                                mime_type: str = None,
                                extension: str = None,
                                resource_config: Dict,
                                disable_encoding_type: bool = False,
                                timeout: int = UNOCONV_DEFAULT_TIMEOUT):
    input_format = _determine_input_format(mime_type, extension)
    if input_format is None:
        raise ValueError('Unsupported input document type.')

    with _s3_object_stream(bucket, key, resource_config, disable_encoding_type) as inputf:
        return _convert_to_pdf(inputf, input_format, timeout)


#
# File based tasks
#


@app.task
def generate_preview_jpg_from_file(*,
                                   file: str,
                                   mime_type: str = None,
                                   height: int = None,
                                   width: int = None,
                                   timeout: int = UNOCONV_DEFAULT_TIMEOUT):
    _, extension = os.path.splitext(file)
    input_format = _determine_input_format(mime_type, extension)
    if input_format is None:
        raise ValueError('Unsupported input document type.')

    with open(file, 'rb') as inputf:
        return _convert_to_image(inputf, input_format, 'jpg', height, width, timeout)


@app.task
def generate_preview_png_from_file(*,
                                   file: str,
                                   mime_type: str = None,
                                   height: int = None,
                                   width: int = None,
                                   timeout: int = UNOCONV_DEFAULT_TIMEOUT):

    _, extension = os.path.splitext(file)
    input_format = _determine_input_format(mime_type, extension)
    if input_format is None:
        raise ValueError('Unsupported input document type.')

    with open(file, 'rb') as inputf:
        return _convert_to_image(inputf, input_format, 'png', height, width, timeout)


@app.task
def generate_pdf_from_file(*, file: str, mime_type: str = None, timeout: int = UNOCONV_DEFAULT_TIMEOUT):
    _, extension = os.path.splitext(file)
    input_format = _determine_input_format(mime_type, extension)
    if input_format is None:
        raise ValueError('Unsupported input document type.')

    with open(file, 'rb') as inputf:
        return _convert_to_pdf(inputf, input_format, timeout)
