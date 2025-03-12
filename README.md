# rococo-email-parser

[![Build Status][build_status_badge]][build_status_link]
[![PyPI version][pypi_badge]][pypi_link]

A Python library to parse emails

## Basic Usage

### Installation

Install using pip:

```bash
pip install rococo-email-parser
```

### Example

```
import rococo.parsers.email as parser

file_path="sample.eml"
mode="rb"

with open(file_path, mode) as f:
    content = f.read()

    email = parser.parse(content)
    print(f"Email subject: {email.subject}")

```



## Deployment

The process described is a Continuous Integration (CI) and Continuous Deployment (CD) pipeline for a Python package using _GitHub Actions_. Here's the breakdown:

### Development Phase

Developers push their changes directly to the main branch.
This branch is likely used for ongoing development work.

### Staging/Testing Phase

When the team is ready to test a potential release, they push the code to a staging branch.
Once the code is pushed to this branch, _GitHub Actions_ automatically publishes the package to the test PyPi server.
The package can then be reviewed and tested by visiting <https://test.pypi.org/project/rococo-email-parser/>.
This step ensures that the package works as expected on the PyPi platform without affecting the live package.

### Release/Publish Phase

When the team is satisfied with the testing and wants to release the package to the public, they create and publish a release on the GitHub repository.
Following this action, _GitHub Actions_ takes over and automatically publishes the package to the official PyPi server.
The package can then be accessed and downloaded by the public at <https://pypi.org/project/rococo-email-parser/>.

In essence, there are three primary phases:

1. Development (main branch)
2. Testing (staging branch with test PyPi server)
3. Release (triggered by a GitHub release and published to the official PyPi server).


### Local Development

To install local Rococo version in other project, upload to your PyPi:
1) Run command "python setup.py sdist" to generate tar.gz file that will be uploaded to PyPi
2) create ./pypirc file in the root of the directory and add:
[pypi]
    username = __token__
    password = THE_TOKEN_PROVIDED_BY_PYPI
3) run the command: twine upload --config-file=./.pypirc dist/*  


[build_status_badge]: https://github.com/EcorRouge/rococo-email-parser/actions/workflows/release-publish.yml/badge.svg
[build_status_link]: https://github.com/EcorRouge/rococo-email-parser/actions/workflows/release-publish.yml
[pypi_badge]: https://badge.fury.io/py/rococo-email-parser.svg
[pypi_link]: https://badge.fury.io/py/rococo-email-parser
