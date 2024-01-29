from setuptools import setup, find_packages

VERSION = "0.0.1"
DESCRIPTION = "tool kit for plotitng analysis results "
LONG_DESCRIPTION = "tool kit for plotitng analysis results "

# Setting up
setup(
    # the name must match the folder name 'verysimplemodule'
    name="anaysis_plot_kit",
    version=VERSION,
    author="Alexander V Dudchenko",
    author_email="<avd@slac.stanford.edu>",
    description=DESCRIPTION,
    long_description=LONG_DESCRIPTION,
    packages=find_packages(),
    install_requires=[
        "sigfig",
        "h5py",
        "quantities",
        "matplotlib",
        "pyyaml",
        "scipy",
        "decimal",
    ],  # add any additional packages that
    # needs to be installed along with your package. Eg: 'caer'
    keywords=["python", "analysis_plot_kit"],
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Education",
        "Programming Language :: Python :: 2",
        "Programming Language :: Python :: 3",
        "Operating System :: MacOS :: MacOS X",
        "Operating System :: Microsoft :: Windows",
    ],
)
