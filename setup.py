import codecs
import os
import re

from setuptools import find_packages, setup

try: # for pip >= 10
    from pip._internal.req import parse_requirements
except ImportError: # for pip <= 9.0.3
    from pip.req import parse_requirements

HERE = os.path.abspath(os.path.dirname(__file__))


# Get the long description
with codecs.open(os.path.join(HERE, "README.rst"), encoding="utf-8") as f:
    long_description = f.read()


# Get version
with open("limpopo/__init__.py", encoding="utf8") as f:
    data = f.read()
    version = re.search(r'__version__ = [\'"](.*?)[\'"]', data).group(1)
    print(version)


def get_requirements(env=None):
    requirements = []
    requirements_filename = "requirements.txt"

    if env:
        requirements_filename = "requirements-{}.txt".format(env)

    requirements = parse_requirements(requirements_filename, session='hack')

    return [str(req.req) for req in requirements]


install_requirements = get_requirements()


setup(
    name="limpopo",
    version=version,
    description="",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="Limpopo",
    platforms=["any"],
    python_requires='>=3.6',
    install_requires=install_requirements,
    include_package_data=True,
    packages=find_packages(exclude=("tests",)),
)
