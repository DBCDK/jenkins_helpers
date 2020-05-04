#!/usr/bin/env python3

from setuptools import setup

setup(name="jenkins-helpers",
    version="0.1.0",
    package_dir={"": "src"},
    packages=["jenkins_helpers"],
    description="",
    provides=["jenkins_helpers"],
    install_requires=["requests"],
    entry_points=
        {"console_scripts": [
            "job-stopper = jenkins_helpers.job_handler:main",
        ]}
    )
