from setuptools import setup, find_packages

with open("README.md") as f:
    readme = f.read()

with open("gym/__init__.py") as f:
    for line in f:
        if line.startswith("__version__"):
            version = line.split('"')[1]

setup(
    name='gym',
    version='0.2.0',
    description='Gym - VNF Testing Framework',
    long_description=readme,
    long_description_content_type="text/markdown",
    author='Raphael Vicente Rosa',
    packages=find_packages(exclude=("tests",)),
    namespace_packages=["gym"],
    include_package_data=True,
    keywords=('gym', 'VNF', 'test', 'benchmark'),
    license='Apache License v2.0',
    url='https://github.com/raphaelvrosa/gym',
    download_url='https://github.com/raphaelvrosa/gym',
    classifiers=[
      'Development Status :: 4 - Beta',
      'Environment :: Other Environment',
      'Intended Audience :: Developers',
      'Operating System :: OS Independent',
      "Programming Language :: Python",
      "Programming Language :: Python :: 3",
      'Programming Language :: Python :: 3.7',
      'Topic :: Utilities',
      'License :: OSI Approved :: Apache Software License',
    ],
    scripts=["gym/agent/gym-agent",
              "gym/monitor/gym-monitor",
              "gym/manager/gym-manager",
              "gym/player/gym-player",
              "gym/infra/gym-infra"],
    install_requires = [
      'asyncio',
      'protobuf',
      'grpclib',
      'grpcio-tools',
      'pyang',
      'pyangbind',
      'jinja2',
      'pyyaml',
      'pandas',
      'docker-py',
      'psutil',
      'paramiko',
      'scp'
    ],
    python_requires=">=3.7",
    setup_requires=["setuptools>=41.1.0"],
)
