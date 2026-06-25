from setuptools import find_packages, setup


setup(
    name="astockdata-local",
    version="0.1.0",
    description="Local A-share data collection and valuation analysis toolkit.",
    package_dir={"": "src"},
    packages=find_packages("src"),
    install_requires=[
        "requests>=2.31",
        "urllib3<2",
    ],
    entry_points={
        "console_scripts": [
            "astock=astockdata.cli:main",
        ],
    },
    python_requires=">=3.9",
)

