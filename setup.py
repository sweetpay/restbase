from setuptools import setup

__version__ = "0.0.1"

setup(
    name="restbase",
    version=__version__,
    author="David Buresund",
    author_email="david.buresund@gmail.com",
    description="Library for building API clients for communicating with REST APIs.",
    license="Apache 2",
    keywords=["api", "apiclient", "rest"],
    url="https://github.com/sweetpay/restbase",
    download_url="https://github.com/sweetpay/restbase/"
                 "tarball/%s" % __version__,
    packages=["restbase"],
    install_requires=["requests>=2.0"]
)
