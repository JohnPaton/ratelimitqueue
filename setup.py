from setuptools import setup


with open("README.md", "r") as h:
    README = h.read()


setup(
    name="ratelimitqueue",
    version="0.2.0",
    description="A thread safe, rate limited queue.",
    long_description=README,
    long_description_content_type="text/markdown",
    url="https://www.github.com/JohnPaton/ratelimitqueue",
    author="John Paton",
    author_email="john@johnpaton.net",
    python_requires=">=3.4",
    packages=["ratelimitqueue"],
    classifiers=[
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.4",
        "Programming Language :: Python :: 3.5",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Development Status :: 4 - Beta",
        "License :: Freely Distributable",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Topic :: Internet",
    ],
)
