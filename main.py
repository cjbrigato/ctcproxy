#!/usr/bin/python
# coding=utf-8

import socket
import select
import time
import sys
import argparse


def get_args(argv=None):
    parser = argparse.ArgumentParser(description="Very Lightweight tcp proxy")
    parser.add_argument('localport', type=int, help="local tcp port")
    parser.add_argument('remotehost', help="remote hostname")
    parser.add_argument('remoteport', type=int, help="remote tcp port")
    parser.add_argument("-v", "--verbose", action='store_true', help="Talks")
    parser.add_argument("-d", "--debug", action='store_true', help="Debugs")
    args = parser.parse_args()
    return args


# Changing the buffer_size/delay can improve the speed or bandwidth
# at the expense of breaking expected behavior
args = get_args(None)
settings = {
    'buffer_size': 4096,
    'delay': 0.0001,
    'remotehost': args.remotehost,
    'remoteport': args.remoteport,
    'localport': args.localport
}


class TermColors:

    HEAD = '\033[95m'
    OK = '\033[92m'
    WARN = '\033[93m'
    INFO = '\033[93m'
    FAIL = '\033[91m'
    REST = '\033[0m'
    BOLD = '\033[1m'
    UNDR = '\033[4m'

TC = TermColors


class Forward:

    def __init__(self):
        self.forward = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    def start(self, host, port):
        try:
            self.forward.connect((host, port))
            return self.forward
        except Exception, e:
            print e
            return False


class CTCProxy:
    input_list = []
    channel = {}

    def __init__(self, host, port):
        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server.bind((host, port))
        self.server.listen(200)

    def main_loop(self):
        self.input_list.append(self.server)
        while 1:
            time.sleep(settings['delay'])
            ss = select.select
            inputready, outputready, exceptready = ss(self.input_list, [], [])
            for self.s in inputready:
                if self.s == self.server:
                    self.on_accept()
                    break

                self.data = self.s.recv(settings['buffer_size'])
                if len(self.data) == 0:
                    self.on_close()
                    break
                else:
                    self.on_recv()

    def on_accept(self):
        forward = Forward().start(
            settings['remotehost'], settings['remoteport'])
        clientsock, clientaddr = self.server.accept()
        if forward:
            if args.verbose:
                print clientaddr, "has connected"
            self.input_list.append(clientsock)
            self.input_list.append(forward)
            self.channel[clientsock] = forward
            self.channel[forward] = clientsock
        else:
            print "Can't establish connection with remote server.",
            print "Closing connection with client side", clientaddr
            clientsock.close()

    def on_close(self):
        if args.verbose:
            print self.s.getpeername(), "has disconnected"
        # remove objects from input_list
        self.input_list.remove(self.s)
        self.input_list.remove(self.channel[self.s])
        out = self.channel[self.s]
        # close the connection with client
        self.channel[out].close()  # equivalent to do self.s.close()
        # close the connection with remote server
        self.channel[self.s].close()
        # delete both objects from channel dict
        del self.channel[out]
        del self.channel[self.s]

    def on_recv(self):
        data = self.data
        # here we can parse and/or modify the data before send forward
        if args.debug:
            print data
        self.channel[self.s].send(data)

if __name__ == '__main__':
    print "::Hello from ctcproxy::"
    print "> Will proxy to", args.remotehost, "port", settings['remoteport']
    print "< From", "0.0.0.0", "port", settings['localport']
    print "--"
    server = CTCProxy('', settings['localport'])
    try:
        server.main_loop()
    except KeyboardInterrupt:
        print "Ctrl C - Stopping server"
        sys.exit(1)
