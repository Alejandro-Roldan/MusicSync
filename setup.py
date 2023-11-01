from setuptools import setup

import musicsync


def readme():
    with open("README.md", encoding="utf-8") as f:
        return f.read()


setup(
    name="musicsync",
    version=musicsync.__version__,
    description="An os.scandir implementation with recursiveness",
    long_description=readme(),
    long_description_content_type="text/markdown",
    url="https://github.com/Alejandro-Roldan/musicsync/tree/master",
    author=musicsync.__author__,
    author_email=musicsync.__email__,
    license=musicsync.__license__,
    packages=["musicsync"],
    entry_points={
        "console_scripts": ["musicsync = musicsync.musicsync:_cli_run"]
    },
    package_data={},
    zip_safe=False,
    python_requires=">=3.11.3",
)
