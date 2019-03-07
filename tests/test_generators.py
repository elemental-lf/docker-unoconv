import os
import subprocess
import unittest
from tempfile import NamedTemporaryFile

from celery import Celery, group
import magic
from parameterized import parameterized

app = Celery('test')
app.config_from_object('celery_unoconv.celeryconfig')
app.conf.update({'broker_url': 'amqp://guest:guest@localhost:5672'})

supported_input_format = app.signature('celery_unoconv.tasks.supported_input_format')
get_input_formats = app.signature('celery_unoconv.tasks.get_input_formats')
get_input_format = app.signature('celery_unoconv.tasks.get_input_format')
generate_preview_jpg = app.signature('celery_unoconv.tasks.generate_preview_jpg')
generate_preview_png = app.signature('celery_unoconv.tasks.generate_preview_png')
generate_pdf = app.signature('celery_unoconv.tasks.generate_pdf')

example_files = [os.path.join(dp, f) for dp, dn, filenames in os.walk('example-files') for f in filenames]


class TestFile(unittest.TestCase):

    # Using file (i.e. libmagic) didn't work out for some MIME types
    @classmethod
    def mime_type(cls, data: str) -> str:
        data_magic = magic.detect_from_content(data)
        if data_magic.mime_type == 'application/octet-stream':
            with NamedTemporaryFile(buffering=0) as f:
                f.write(data)
                result = subprocess.run(['xdg-mime', 'query', 'filetype', f.name], stdout=subprocess.PIPE)
            mime_type = result.stdout.decode('utf-8', errors='ignore').rstrip()
        else:
            mime_type = data_magic.mime_type
        return mime_type

    @parameterized.expand([('jpg',), ('png',), ('pdf',)])
    def test_generator_functions(self, output_format: str):
        tasks = []
        input_files = []

        os.makedirs('./output_{}'.format(output_format), exist_ok=True)

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
            with open(input_file, 'rb') as f:
                data = f.read()
            data_mime_type = self.mime_type(data)
            _, extension = os.path.splitext(input_file)

            if not supported_input_format.delay(mime_type=data_mime_type, extension=extension).get():
                print('{}: Unsupported MIME type {}.'.format(input_file, data_mime_type))
                continue

            input_files.append(input_file)
            if output_format == 'pdf':
                tasks.append(
                    generator.clone(kwargs={
                        'data': data,
                        'mime_type': data_mime_type,
                        'extension': extension,
                        'timeout': 10,
                    }))
            else:
                tasks.append(
                    generator.clone(
                        kwargs={
                            'data': data,
                            'mime_type': data_mime_type,
                            'extension': extension,
                            'height': 800,
                            'width': 800,
                            'timeout': 10,
                        }))

        group_results = group(tasks).apply_async()

        failed_jobs = 0
        successful_jobs = 0
        for input_file, result in zip(input_files, group_results.get(propagate=False)):
            if isinstance(result, Exception):
                print('{}: exception {}.'.format(input_file, str(result)))
                failed_jobs += 1
                continue

            result_mime_type = self.mime_type(result)
            self.assertTrue(expected_mime_type, result_mime_type)
            with open('./output_{}/{}.{}'.format(output_format, input_file.replace('/', '_'), output_format), 'wb') as f:
                f.write(result)
            successful_jobs += 1

        self.assertEqual(44, group_results.completed_count())
        self.assertEqual(44, successful_jobs)
        self.assertEqual(0, failed_jobs)


if __name__ == '__main__':
    unittest.main()
