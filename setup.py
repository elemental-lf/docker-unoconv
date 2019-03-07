try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup

with open('requirements.txt', 'r', encoding='utf-8') as f:
    requirements = [line.rstrip() for line in f]

with open('requirements_dev.txt', 'r', encoding='utf-8') as f:
    requirements_dev = [line.rstrip() for line in f]

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
    install_requires=requirements,
    extras_require={
        'dev': requirements_dev,
    },
)
