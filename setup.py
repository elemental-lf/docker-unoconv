try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup

setup(
    name='celery_unoconv',
    version='0.1.0',
    description='Celery tasks for driving unoconv',
    url='http://github.com/elemental-lf/docker-unoconv',
    author='Lars Fenneberg',
    author_email='lf@elemental.net',
    license='GPL-3',
    packages=['celery_unoconv'],
    zip_safe=False,
    python_requires='~=3.6',
    install_requires=[
        'boto3==1.9.106',
        'celery==4.3.0rc2',
    ],
    extras_require={
        'dev': [
            'parameterized>=0.7.0,<1',
            'file-magic>=0.4.0,<1',
        ],
    },
)
