import os
import subprocess
import unittest
import warnings
from io import BytesIO

from PIL import Image
from fs import open_fs
from celery import Celery, group
import magic
from fs.copy import copy_file
from parameterized import parameterized

app = Celery('test_generators')
app.config_from_object('unoconv.celeryconfig')
app.conf.update({'broker_url': 'amqp://guest:guest@localhost:5672'})

supported_import_format = app.signature('unoconv.tasks.supported_import_format')
generate_preview_jpg = app.signature('unoconv.tasks.generate_preview_jpg')
generate_preview_png = app.signature('unoconv.tasks.generate_preview_png')
generate_pdf = app.signature('unoconv.tasks.generate_pdf')

example_files = [os.path.join(dp, f) for dp, dn, filenames in os.walk('example-files') for f in filenames]


class TestFile(unittest.TestCase):

    BUCKET_NAME_INPUT = 'unoconv-input'
    BUCKET_NAME_OUTPUT = 'unoconv-output'

    INPUT_FS_URL_HOST = f's3://minio:minio123@{BUCKET_NAME_INPUT}?endpoint_url=http://localhost:9000'
    INPUT_FS_URL = f's3://minio:minio123@{BUCKET_NAME_INPUT}?endpoint_url=http://minio:9000'
    OUTPUT_FS_URL_HOST = f's3://minio:minio123@{BUCKET_NAME_OUTPUT}?endpoint_url=http://localhost:9000'
    OUTPUT_FS_URL = f's3://minio:minio123@{BUCKET_NAME_OUTPUT}?endpoint_url=http://minio:9000'

    PIXE_HEIGHT = 800
    PIXEL_WIDTH = 800
    LOGICAL_HEIGHT = 20000
    LOGICAL_WIDTH = 20000

    @classmethod
    def setUpClass(cls):
        # This disables ResourceWarnings from boto3 which are normal
        # See: https://github.com/boto/boto3/issues/454
        warnings.filterwarnings(
            "ignore", category=ResourceWarning, message=r'unclosed.*<(?:ssl.SSLSocket|socket\.socket).*>')

        os.makedirs('output', exist_ok=True)
        with open_fs('osfs://output/') as fs:
            fs.glob("**").remove()

    def setUp(self):
        with open_fs(self.INPUT_FS_URL_HOST) as fs:
            fs.glob("**").remove()
        with open_fs(self.OUTPUT_FS_URL_HOST) as fs:
            fs.glob("**").remove()

    def tearDown(self):
        with open_fs(self.INPUT_FS_URL_HOST) as fs:
            fs.glob("**").remove()
        with open_fs(self.OUTPUT_FS_URL_HOST) as fs:
            fs.glob("**").remove()

    # Using file (i.e. libmagic) didn't work out for some MIME types
    @staticmethod
    def mime_type(file: str) -> str:
        data_magic = magic.detect_from_filename(file)
        if data_magic.mime_type == 'application/octet-stream':
            result = subprocess.run(['xdg-mime', 'query', 'filetype', file], stdout=subprocess.PIPE)
            mime_type = result.stdout.decode('utf-8', errors='ignore').rstrip()
        else:
            mime_type = data_magic.mime_type
        return mime_type

    @parameterized.expand([
        ('jpg', False, False),
        ('png', False, False),
        ('pdf', False, False),
        ('jpg', True, False),
        ('png', True, False),
        ('jpg', False, True),
        ('png', False, True),
    ])
    def test_generator_functions(self, output_format: str, scale_height: bool, scale_width: bool):
        tasks = []
        input_files = []

        if output_format == 'jpg':
            generator = generate_preview_jpg
            expected_mime_type = 'image/jpeg'
        elif output_format == 'png':
            generator = generate_preview_png
            expected_mime_type = 'image/png'
        elif output_format == 'pdf':
            generator = generate_pdf
            expected_mime_type = 'application/pdf'
        else:
            raise RuntimeError('Unsupported output format {}.'.format(output_format))

        for input_file in example_files:
            data_mime_type = self.mime_type(input_file)
            _, extension = os.path.splitext(input_file)

            if not supported_import_format.delay(mime_type=data_mime_type, extension=extension).get():
                print('{}: Unsupported MIME type {}.'.format(input_file, data_mime_type))
                continue
            input_file_basename = os.path.basename(input_file)
            input_files.append(input_file_basename)

            with open_fs('osfs://') as source_fs, open_fs(self.INPUT_FS_URL_HOST) as destination_fs:
                copy_file(source_fs, input_file, destination_fs, input_file_basename)

            if scale_height:
                pixel_height = None
                pixel_width = self.PIXEL_WIDTH
                logical_height = None
                logical_width = self.LOGICAL_WIDTH
            elif scale_width:
                pixel_height = self.PIXE_HEIGHT
                pixel_width = None
                logical_height = self.LOGICAL_HEIGHT
                logical_width = None
            else:
                pixel_height = self.PIXE_HEIGHT
                pixel_width = self.PIXEL_WIDTH
                logical_height = self.LOGICAL_HEIGHT
                logical_width = self.LOGICAL_WIDTH

            output_file = '{input_file_basename}-{height}x{width}.{output_format}'.format(
                input_file_basename=input_file_basename,
                height=pixel_height if pixel_height else 'auto',
                width=pixel_width if pixel_width else 'auto',
                output_format=output_format)
            if output_format == 'pdf':
                tasks.append(
                    generator.clone(
                        kwargs={
                            'input_fs_url': self.INPUT_FS_URL,
                            'input_file': input_file_basename,
                            'output_fs_url': self.OUTPUT_FS_URL,
                            'output_file': output_file,
                            'mime_type': data_mime_type,
                            'extension': extension,
                            'paper_format': 'LETTER',
                            'timeout': 10,
                        }))
            elif output_format == 'jpg':
                tasks.append(
                    generator.clone(
                        kwargs={
                            'input_fs_url': self.INPUT_FS_URL,
                            'input_file': input_file_basename,
                            'output_fs_url': self.OUTPUT_FS_URL,
                            'output_file': output_file,
                            'mime_type': data_mime_type,
                            'extension': extension,
                            'pixel_height': pixel_height,
                            'pixel_width': pixel_width,
                            'logical_height': logical_height,
                            'logical_width': logical_width,
                            'quality': 25,
                            'scale_height': scale_height,
                            'scale_width': scale_width,
                            'timeout': 10,
                        }))
            elif output_format == 'png':
                tasks.append(
                    generator.clone(
                        kwargs={
                            'input_fs_url': self.INPUT_FS_URL,
                            'input_file': input_file_basename,
                            'output_fs_url': self.OUTPUT_FS_URL,
                            'output_file': output_file,
                            'mime_type': data_mime_type,
                            'extension': extension,
                            'pixel_height': pixel_height,
                            'pixel_width': pixel_width,
                            'logical_height': logical_height,
                            'logical_width': logical_width,
                            'compression': 3,
                            'scale_height': scale_height,
                            'scale_width': scale_width,
                            'timeout': 10,
                        }))
            else:
                raise NotImplementedError

        group_results = group(tasks).apply_async()

        failed_jobs = 0
        successful_jobs = 0
        expected_jobs = len(input_files)
        for input_file_basename, result in zip(input_files, group_results.get(propagate=False)):
            if isinstance(result, Exception):
                print('{}: exception {}.'.format(input_file_basename, str(result)))
                failed_jobs += 1
                continue

            output_file = '{input_file_basename}-{height}x{width}.{output_format}'.format(
                input_file_basename=input_file_basename,
                height=pixel_height if pixel_height else 'auto',
                width=pixel_width if pixel_width else 'auto',
                output_format=output_format)
            with open_fs(self.OUTPUT_FS_URL_HOST) as source_fs, open_fs('osfs://output/') as destination_fs:
                copy_file(source_fs, output_file, destination_fs, output_file)

            output_mime_type = self.mime_type(f'output/{output_file}')
            self.assertTrue(expected_mime_type, output_mime_type)

            if output_format == 'jpg' or output_format == 'png':
                with open(f'output/{output_file}', 'rb') as f:
                    output_data = BytesIO(f.read())

                image = Image.open(output_data)

                if scale_height:
                    self.assertEqual(self.PIXEL_WIDTH, image.width)
                elif scale_width:
                    self.assertEqual(self.PIXE_HEIGHT, image.height)
                else:
                    self.assertEqual(self.PIXE_HEIGHT, image.height)
                    self.assertEqual(self.PIXEL_WIDTH, image.width)

            successful_jobs += 1

        self.assertEqual(expected_jobs, group_results.completed_count())
        self.assertEqual(expected_jobs, successful_jobs)
        self.assertEqual(0, failed_jobs)


if __name__ == '__main__':
    unittest.main()
