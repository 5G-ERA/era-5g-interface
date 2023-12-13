import logging
import os
import socket
import time
from contextlib import closing
from threading import Event, Thread
from typing import Dict
from unittest import mock

import pytest
import socketio
from flask import Flask

from era_5g_interface.channels import DATA_NAMESPACE, CallbackInfoClient, CallbackInfoServer, ChannelType
from era_5g_interface.client_channels import ClientChannels
from era_5g_interface.server_channels import ServerChannels


def find_free_port():
    with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as s:
        s.bind(("", 0))
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        return s.getsockname()[1]


@pytest.mark.timeout(10)
def test_channels() -> None:
    port = find_free_port()
    sio = socketio.Server()
    os._exit = mock.MagicMock()

    def thread_flask() -> None:
        app = Flask(__name__)
        app.wsgi_app = socketio.WSGIApp(sio, app.wsgi_app)  # type: ignore

        logging.getLogger().info("Starting Flask...")
        app.run(port=port, host="0.0.0.0")

    t = Thread(target=thread_flask)
    t.daemon = True
    t.start()

    test_data = {"test": "data"}
    server_got_data = Event()

    def server_json_callback(sid: str, data: Dict) -> None:
        assert data == test_data
        server_got_data.set()

    def server_json_exc_callback(sid: str, data: Dict) -> None:
        raise Exception("Boom from server!")

    def client_json_callback(data: Dict) -> None:
        pass

    def client_json_exc_callback(data: Dict) -> None:
        raise Exception("Boom from client!")

    server = ServerChannels(
        sio,
        {
            "test": CallbackInfoServer(ChannelType.JSON, server_json_callback),
            "test_lz4": CallbackInfoServer(ChannelType.JSON_LZ4, server_json_callback),
            "test_exception": CallbackInfoServer(ChannelType.JSON, server_json_exc_callback),
        },
        disconnect_callback=None,
    )

    client = socketio.Client()
    time.sleep(1)  # not sure why wait_timeout is not enough
    client.connect(f"http://localhost:{port}", wait_timeout=5, namespaces=[DATA_NAMESPACE])

    client_ch = ClientChannels(
        client,
        {
            "test": CallbackInfoClient(ChannelType.JSON, client_json_callback),
            "test_exception": CallbackInfoClient(ChannelType.JSON, client_json_exc_callback),
        },
        disconnect_callback=None,
    )
    client_ch.send_data(test_data, "test")
    assert server_got_data.wait(1)
    server_got_data.clear()

    client_ch.send_data(test_data, "test_lz4", channel_type=ChannelType.JSON_LZ4)
    assert server_got_data.wait(1)
    server_got_data.clear()

    # test exception handling in server callback
    client_ch.send_data(test_data, "test_exception", channel_type=ChannelType.JSON)
    assert not server_got_data.wait(1)
    assert os._exit.called

    os._exit.reset_mock()

    # test exception handling in client callback
    server.send_data(test_data, "test_exception", channel_type=ChannelType.JSON, sid=client.get_sid(DATA_NAMESPACE))
    assert not server_got_data.wait(1)
    assert os._exit.called
