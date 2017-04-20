from setuptools import setup, find_packages

requires = ["click", "pandas", "pymongo", "dictproxyhack", "python-dateutil", "redis"]

try:
    import enum
except ImportError:
    requires.append("enum34")

setup(
    name="fxdayu",
    version="0.1",
    packages=find_packages(exclude=["examples", "examples.*"]),
    include_package_data=True,
    author="xinge.BurdenBear;xinge.CaiMeng",
    author_email="public@fxdayu.com",
    description="This is an python event-driven trader engine",
    license="MIT",
    keywords="",
    url="http://act.fxdayu.com/academy/tutorials.html",
    install_requires=requires
)
