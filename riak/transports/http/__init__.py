"""
Copyright 2010 Rusty Klophaus <rusty@basho.com>
Copyright 2010 Justin Sheehy <justin@basho.com>
Copyright 2009 Jay Baird <jay@mochimedia.com>

This file is provided to you under the Apache License,
Version 2.0 (the "License"); you may not use this file
except in compliance with the License.  You may obtain
a copy of the License at

  http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing,
software distributed under the License is distributed on an
"AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
KIND, either express or implied.  See the License for the
specific language governing permissions and limitations
under the License.
"""

from __future__ import absolute_import

import http.client
import socket
from riak.transports.pool import Pool
from riak.transports.http.transport import RiakHttpTransport


class NoNagleHTTPConnection(http.client.HTTPConnection):

    """
    Setup a connection class which does not use Nagle - deal with
    latency on PUT requests lower than MTU
    """

    def connect(self):
        """
        Set TCP_NODELAY on socket
        """
        http.client.HTTPConnection.connect(self)
        self.sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)


class RiakHttpPool(Pool):

    """
    A pool of HTTP(S) transport connections.
    """

    def __init__(self, client, **options):
        self.client = client
        self.options = options
        if client.protocol == 'https':
            self.connection_class = http.client.HTTPSConnection
        else:
            self.connection_class = NoNagleHTTPConnection
        super(RiakHttpPool, self).__init__()

    def create_resource(self):
        node = self.client._choose_node()
        return RiakHttpTransport(node=node,
                                 client=self.client,
                                 connection_class=self.connection_class,
                                 **self.options)

    def destroy_resource(self, transport):
        transport.close()


CONN_CLOSED_ERRORS = (
    http.client.NotConnected,
    http.client.IncompleteRead,
    http.client.ImproperConnectionState,
    http.client.BadStatusLine
)


def is_retryable(err):
    """
    Determines if the given exception is something that is
    network/socket-related and should thus cause the HTTP connection
    to close and the operation retried on another node.

    :rtype: boolean
    """
    for errtype in CONN_CLOSED_ERRORS:
        if isinstance(err, errtype):
            return True
    return False
