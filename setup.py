from setuptools import setup, find_packages

# Dont install pygdal_utils
with open("./requirements.txt") as reqs:
    requirements = [line.rstrip() for line in reqs if "git" not in line]

setup(
    name="gdaljson",
    version="0.1",
    description="JSON wrapper of the GDAL VRT spec",
    author="Jeff Albrecht",
    author_email="geospatialjeff@gmail.com",
    packages=find_packages(exclude=["tests"]),
    install_requires=requirements,
    entry_points={
        "console_scripts": [
            "warp=gdaljson.warp_cli:cli",
            "translate=gdaljson.translate_cli:cli",
        ]
    },
)
