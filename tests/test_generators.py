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

supported_import_format = app.signature('unoconv.tasks.supported_import_format')
generate_preview_jpg = app.signature('unoconv.tasks.generate_preview_jpg')
generate_preview_png = app.signature('unoconv.tasks.generate_preview_png')
generate_pdf = app.signature('unoconv.tasks.generate_pdf')

example_files = [os.path.join(dp, f) for dp, dn, filenames in os.walk('example-files') for f in filenames]
if not example_files:
    raise RuntimeError('Example files not found.')


class TestFile(unittest.TestCase):

    BUCKET_NAME_INPUT = 'unoconv-input'
    BUCKET_NAME_OUTPUT = 'unoconv-output'

    INPUT_FS_URL_HOST = f's3://minio:minio123@{BUCKET_NAME_INPUT}?endpoint_url=http://localhost:9000'
    INPUT_FS_URL = f's3://minio:minio123@{BUCKET_NAME_INPUT}?endpoint_url=http://minio:9000'
    OUTPUT_FS_URL_HOST = f's3://minio:minio123@{BUCKET_NAME_OUTPUT}?endpoint_url=http://localhost:9000'
    OUTPUT_FS_URL = f's3://minio:minio123@{BUCKET_NAME_OUTPUT}?endpoint_url=http://minio:9000'

    PIXE_HEIGHT = 800
    PIXEL_WIDTH = 800

    @classmethod
    def setUpClass(cls):
        # This disables ResourceWarnings from boto3 which are normal
        # See: https://github.com/boto/boto3/issues/454
        warnings.filterwarnings(
            "ignore", category=ResourceWarning, message=r'unclosed.*<(?:ssl.SSLSocket|socket\.socket).*>')

        os.makedirs('output', exist_ok=True)
        with open_fs('osfs://output/') as fs:
            fs.glob("**").remove()

    @classmethod
    def tearDownClass(cls):
        with open_fs(cls.INPUT_FS_URL_HOST) as fs:
            fs.glob("**").remove()
        with open_fs(cls.OUTPUT_FS_URL_HOST) as fs:
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
        ('jpg', 'jpg_', 'jpg', False),
        ('png', 'png_', 'png', False),
        ('pdf', 'pdf_', 'pdf', False),
        ('jpg maintain ratio', 'jpgmr_', 'jpg', True),
        ('png maintain ratio', 'pngmr_', 'png', True),
    ])
    def test_generator_functions(self, _, bucket_prefix: str, output_format: str, maintain_ratio: bool):
        tasks = []
        output_files = []

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
            destination_input_file = '{bucket_prefix}{input_file_basename}'.format(
                bucket_prefix=bucket_prefix, input_file_basename=os.path.basename(input_file))

            with open_fs('osfs://') as source_fs, open_fs(self.INPUT_FS_URL_HOST) as destination_fs:
                copy_file(source_fs, input_file, destination_fs, destination_input_file)

            pixel_height = self.PIXE_HEIGHT
            pixel_width = self.PIXEL_WIDTH

            output_file = '{input_file}.{output_format}'.format(
                input_file=destination_input_file, output_format=output_format)
            output_files.append(output_file)
            if output_format == 'pdf':
                tasks.append(
                    generator.clone(
                        kwargs={
                            'input_fs_url': self.INPUT_FS_URL,
                            'input_file': destination_input_file,
                            'output_fs_url': self.OUTPUT_FS_URL,
                            'output_file': output_file,
                            'mime_type': data_mime_type,
                            'extension': extension,
                            'paper_format': 'LETTER',
                            'timeout': 100,
                        }))
            elif output_format == 'jpg':
                tasks.append(
                    generator.clone(
                        kwargs={
                            'input_fs_url': self.INPUT_FS_URL,
                            'input_file': destination_input_file,
                            'output_fs_url': self.OUTPUT_FS_URL,
                            'output_file': output_file,
                            'mime_type': data_mime_type,
                            'extension': extension,
                            'pixel_height': pixel_height,
                            'pixel_width': pixel_width,
                            'quality': 25,
                            'maintain_ratio': maintain_ratio,
                            'timeout': 20,
                        }))
            elif output_format == 'png':
                tasks.append(
                    generator.clone(
                        kwargs={
                            'input_fs_url': self.INPUT_FS_URL,
                            'input_file': destination_input_file,
                            'output_fs_url': self.OUTPUT_FS_URL,
                            'output_file': output_file,
                            'mime_type': data_mime_type,
                            'extension': extension,
                            'pixel_height': pixel_height,
                            'pixel_width': pixel_width,
                            'compression': 3,
                            'maintain_ratio': maintain_ratio,
                            'timeout': 20,
                        }))
            else:
                raise NotImplementedError

        group_results = group(tasks).apply_async()
        failed_jobs = 0
        successful_jobs = 0
        expected_jobs = len(output_files)
        for output_file, result in zip(output_files, group_results.get(propagate=False)):
            if isinstance(result, Exception):
                print('{}: exception {}.'.format(output_file, str(result)))
                failed_jobs += 1
                continue

            with open_fs(self.OUTPUT_FS_URL_HOST) as source_fs, open_fs('osfs://output/') as destination_fs:
                copy_file(source_fs, output_file, destination_fs, output_file)

            output_mime_type = self.mime_type(f'output/{output_file}')
            self.assertTrue(expected_mime_type, output_mime_type)

            if output_format == 'jpg' or output_format == 'png':
                with open(f'output/{output_file}', 'rb') as f:
                    output_data = BytesIO(f.read())

                image = Image.open(output_data)

                if maintain_ratio:
                    self.assertTrue(image.height == self.PIXE_HEIGHT or image.width == self.PIXEL_WIDTH)
                else:
                    self.assertEqual(self.PIXE_HEIGHT, image.height)
                    self.assertEqual(self.PIXEL_WIDTH, image.width)

            successful_jobs += 1

        self.assertEqual(expected_jobs, group_results.completed_count())
        self.assertEqual(expected_jobs, successful_jobs)
        self.assertEqual(0, failed_jobs)


if __name__ == '__main__':
    unittest.main()
