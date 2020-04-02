import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="openerz-api",
    version="0.1.0",
    author="Michał Ziemski",
    author_email="michal@terrestryal.com",
    description="A Python wrapper around the OpenERZ API.",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/misialq/openerz-api",
    packages=setuptools.find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    install_requires=["requests",],
    python_requires=">=3.6",
)
