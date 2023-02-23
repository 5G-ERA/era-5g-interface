# era-5g-interface
Python interface (support classes) for Net Applications.

## Installation

The package could be installed via pip:

```bash
pip install era_5g_interface
```

## Classes

### ThreadBase (common.py)

Base Thread class which provides common methods.

### TaskHandler (task_handler.py)

Abstract class. Thread-based task handler which takes care of receiving data from the NetApp client and passing them to the NetApp worker.

### TaskHandlerGstreamer (task_handler_gstreamer.py)

Abstract class. Task handler which takes care of reading the data from Gstreamer pipeline with defined parameters. It needs to be inherited to implement the store_image method.

### TaskHandlerInternalQ (task_handler_internal_q.py)

Task handler which takes care of passing the data to the python internal queue for future processing. It could either be inherited to implement the _run method and read the data from any source or used directly and call the store_image method externaly.

### TaskHandlerGstreamerInternalQ (task_handler_gstreamer_internal_q.py)

Task handler which combines the Gstreamer functionality of data retrieval with usage of python internal queues for passing the data to the worker object.

## Contributing, development

- Any contribution should go through a pull request from your fork.
- Before committing, please run locally:
  - `./pants fmt ::` - format all code according to our standard.
  - `./pants lint ::` - checks formatting and few more things.
  - `./pants check ::` - runs type checking (mypy).
- The same checks will be run within CI.
- A virtual environment with all necessary dependencies can be generated using `./pants export ::`. 
  You may then activate the environment and add `era_5g_interface` to your `PYTHONPATH`, which is equivalent 
  to installing a package using `pip install -e`.
- To generate distribution packages (`tar.gz` and `whl`), you may run `./pants package ::`.
- For commit messages, please stick to 
  [https://www.conventionalcommits.org/en/v1.0.0/](https://www.conventionalcommits.org/en/v1.0.0/).