from distutils.core import setup

from os import path
this_directory = path.abspath(path.dirname(__file__))
with open(path.join(this_directory, 'README.md'), encoding='utf-8') as f:
    long_description = f.read()


setup(
    name='ticketleap',
    packages=['ticketleap'],
    version='1.0.0',
    license='MIT',
    description=
    'Unofficial TicketLeap API. Create and modify TicketLeap events at scale',
    long_description=long_description,
    long_description_content_type='text/markdown',
    author='Connor Skees',
    author_email='connor1skees@gmail.com',
    url='https://github.com/connorskees/ticketleap',
    download_url=
    'https://github.com/ConnorSkees/ticketleap/archive/v1.0.0.tar.gz',
    keywords=['ticketleap', 'api'],
    install_requires=[
        'requests',
        'beautifulsoup4',
    ],
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Intended Audience :: Developers',
        'Topic :: Software Development :: Build Tools',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3.6',
    ],
)
