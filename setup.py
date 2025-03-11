from setuptools import find_packages, setup

setup(
    name='rococo-email-parser',
    version='1.0.0',
    packages=find_packages(),
    url='https://github.com/EcorRouge/rococo-email-parser',
    license='MIT',
    author='Jay Grieves',
    author_email='jaygrieves@gmail.com',
    description='A Python library to parse emails',
    entry_points={
        'console_scripts': [
        ],
    },
    long_description=open('README.md').read(),
    long_description_content_type='text/markdown',
    install_requires=[
        'pydantic>=2.1.0',
        'beautifulsoup4==4.12.2'
    ],
    python_requires=">=3.10"
)
