python_sources(name="lib")

resources(name="py.typed", sources=["py.typed"])

python_distribution(
    name="dist",
    dependencies=[":lib", ":py.typed", "era_5g_interface/dataclasses:dataclasses", "era_5g_interface/utils:utils"],
    wheel=True,
    sdist=True,
    provides=setup_py(
        name="era_5g_interface",
        version="0.6.1",
        description="An interface for 5G-ERA NetApps",
        author="Michal Kapinus",
        author_email="ikapinus@fit.vutbr.cz",
        license="LGPL",
        python_requires=">=3.8",
        classifiers=[
            "Programming Language :: Python :: 3",
            "License :: OSI Approved :: GNU Lesser General Public License v3 (LGPLv3)",
            "Operating System :: OS Independent",
            "Intended Audience :: Developers",
        ],
    ),
)
