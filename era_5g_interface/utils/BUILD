python_sources(
    name="utils",
    skip_mypy=True,
    skip_black=True,
    skip_flake8=True,
)

# this is to force flake8/mypy to test with different versions of Python
python_sources(name="utils_py38", interpreter_constraints=["==3.8.*"])
python_sources(name="utils_py39", interpreter_constraints=["==3.9.*"])
python_sources(name="utils_py310", interpreter_constraints=["==3.10.*"])
