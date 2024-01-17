# era-5g-interface

Python interface (support classes) for 5G-ERA Network Applications.

## Related Repositories

- [era-5g-client](https://github.com/5G-ERA/era-5g-client) - client classes for 5G-ERA Network Applications with 
  various transport options.
- [era-5g-server](https://github.com/5G-ERA/era-5g-server) - server classes for 5G-ERA Network Applications with 
  various transport options.
- [Reference-NetApp](https://github.com/5G-ERA/Reference-NetApp) - reference 5G-ERA Network Application implementation 
  with MMCV detector.

## Installation

The package could be installed via pip:

```bash
pip install era_5g_interface
```

## Classes

### Channels ([channels.py](era_5g_interface/channels.py))

Channels class is used to define bidirectional channel data callbacks and contains send functions. It handles image 
frames JPEG, H.264 and HEVC frame encoding/decoding. The class cannot be used alone. The ServerChannels and ClientChannels 
classes create callbacks and encoders/decoders.

### ClientChannels and ServerChannels ([client_channels.py](era_5g_interface/client_channels.py), [server_channels.py](era_5g_interface/server_channels.py))

ClientChannels and ServerChannels classes are used to define bidirectional channel (image and JSON) callbacks and contains 
send functions. They are used inside the NetAppClientBase in era_5g_client and NetworkApplicationServer in 
era_5g_server. ServerChannels is used with Socketio Server object, ClientChannels is used with Socketio Client object.

### FrameDecoder and FrameEncoder ([frame_decoder.py](era_5g_interface/frame_decoder.py), [frame_encoder.py](era_5g_interface/frame_encoder.py))

FrameDecoder and FrameEncoder classes providing video frame encoding and decoding.

### TaskHandlerInternalQ ([task_handler_internal_q.py](era_5g_interface/task_handler_internal_q.py))

Task handler which takes care of passing the data to the python internal queue for future processing. 

## Contributing, development

- The package is developed and tested with Python 3.8.
- Any contribution should go through a pull request from your fork.
- We use Pants to manage the code ([how to install it](https://www.pantsbuild.org/docs/installation)).
- Before committing, please run locally:
  - `pants fmt ::` - format all code according to our standard.
  - `pants lint ::` - checks formatting and few more things.
  - `pants check ::` - runs type checking (mypy).
  - `pants test ::` - runs Pytest tests.
- The same checks will be run within CI.
- A virtual environment with all necessary dependencies can be generated using `pants export ::`. 
  You may then activate the environment and add `era_5g_interface` to your `PYTHONPATH`, which is equivalent 
  to installing a package using `pip install -e`.
- To generate distribution packages (`tar.gz` and `whl`), you may run `pants package ::`.
- For commit messages, please stick to
  [https://www.conventionalcommits.org/en/v1.0.0/](https://www.conventionalcommits.org/en/v1.0.0/).
