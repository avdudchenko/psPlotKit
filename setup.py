from setuptools import setup, find_packages

VERSION = "0.0.1"
DESCRIPTION = (
    "tool kit for importing and plotting result generated by parameter sweep tool"
)
LONG_DESCRIPTION = "tool kit for plotting analysis results "

# Setting up
setup(
    # the name must match the folder name 'verysimplemodule'
    name="waterTapAbox",
    version=VERSION,
    author="Alexander V Dudchenko",
    author_email="<avd@slac.stanford.edu>",
    description=DESCRIPTION,
    long_description=LONG_DESCRIPTION,
    packages=find_packages(),
    python_requires=">=3.8",
    install_requires=[
        "sigfig",
        "h5py",
        "quantities",
        "matplotlib",
        "pyyaml",
        "scipy",
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
