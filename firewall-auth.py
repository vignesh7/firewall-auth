#!/usr/bin/python

# Copyright (c) 2009 Siddharth Agarwal
#
# Permission is hereby granted, free of charge, to any person
# obtaining a copy of this software and associated documentation
# files (the "Software"), to deal in the Software without
# restriction, including without limitation the rights to use,
# copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the
# Software is furnished to do so, subject to the following
# conditions:
#
# The above copyright notice and this permission notice shall be
# included in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES
# OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
# NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT
# HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY,
# WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
# FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR
# OTHER DEALINGS IN THE SOFTWARE.

import getpass
import httplib
import urllib
import urlparse
import re
from optparse import OptionParser
import sys
import logging
import time

def InitLogger(options):
  logger = logging.getLogger("FirewallLogger")
  logger.setLevel(logging.DEBUG)
  handler = logging.StreamHandler()
  if options.verbose:
    handler.setLevel(logging.DEBUG)
  else:
    handler.setLevel(logging.INFO)

  formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
  handler.setFormatter(formatter)
  logger.addHandler(handler)

def FirewallKeepAlive(url):
  while 1:
    logger = logging.getLogger("FirewallLogger")
    logger.info("Sending request to keep alive")
    # Connect to the firewall
    conn = httplib.HTTPSConnection(url.netloc)
    conn.request("GET", url.path + "?" + url.query)
    response = conn.getresponse()

    logger.debug(str(response.status))
    logger.debug(response.read())

    conn.close()

    # Set a timer
    time.sleep(200);

"""
This checks whether we're logged in already
"""
def IsLoggedIn():
  # Connect to Google, see if we can connect or not. We use the IP directly here
  # so that this runs on computers even if they don't have DNS configured.
  conn = httplib.HTTPConnection("74.125.67.100:80")
  conn.request("GET", "/")
  response = conn.getresponse()
  # 303 leads to the auth page, which means we aren't logged in
  return not (response.status == 303)

def FirewallAuth(username, password):
  logger = logging.getLogger("FirewallLogger")
  if not IsLoggedIn():
    authLocation = response.getheader("Location")
    conn.close()
    logger.info("The auth location is: " + authLocation)

    # Make a connection to the auth location
    parsedAuthLocation = urlparse.urlparse(authLocation)
    authConn = httplib.HTTPSConnection(parsedAuthLocation.netloc)
    authConn.request("GET", parsedAuthLocation.path + "?" + parsedAuthLocation.query)
    authResponse = authConn.getresponse()
    data = authResponse.read()
    authConn.close()

    # Look for the right magic value in the data
    match = re.search(r"VALUE=\"([0-9a-f]+)\"", data)
    magicString = match.group(1)
    logger.debug("The magic string is: " + magicString)

    # Now construct a POST request
    params = urllib.urlencode({'username': username, 'password': password,
                               'magic': magicString, '4Tredir': '/'})
    headers = {"Content-Type": "application/x-www-form-urlencoded",
               "Accept": "text/plain"}

    postConn = httplib.HTTPSConnection(parsedAuthLocation.netloc)
    postConn.request("POST", "/", params, headers)

    # Get the response
    postResponse = postConn.getresponse()

    postData = postResponse.read()
    postConn.close()

    # Look for the keepalive URL
    keepaliveMatch = re.search(r"location.href=\"(.+?)\"", postData)
    if keepaliveMatch is None:
      # Whoops, unsuccessful -- probably the username and password didn't match
      logger.fatal("Authentication unsuccessful, check your username and password")
      return 3

    keepaliveURL = keepaliveMatch.group(1)

    logger.info("The keep alive URL is: " + keepaliveURL)
    logger.debug(postData)
    FirewallKeepAlive(urlparse.urlparse(keepaliveURL))

  else:
    logger.fatal(("Server returned %d %s, so we cannot proceed. Are you " +
                 "already authenticated?") %
                 (response.status, httplib.responses[response.status]))
    return 2

"""
Get the username and password either from command line args or interactively
"""
def GetUsernameAndPassword(args):
  username = None
  if len(args) == 0:
    # Get the username from the input
    print "Username: ",
    username = sys.stdin.readline()
  else:
    # First member of args
    username = args[0]

  password = None
  if len(args) <= 1:
    # Read the password without echoing it
    password = getpass.getpass()
  else:
    password = args[1]

  return (username, password)

"""
Main function
"""
def main(argv = None):
  if argv is None:
    argv = sys.argv[1:]

  # First generate help syntax
  usage = "Usage: %prog [options] username password"
  parser = OptionParser(usage = usage)
  parser.add_option("-v", "--verbose", action = "store_true", dest = "verbose",
                    help = "Print lots of debugging information")

  # Parse arguments
  (options, args) = parser.parse_args(argv)

  if len(args) > 2:
    parser.error("too many arguments")
    return 1

  InitLogger(options)

  # Try authenticating!
  (username, password) = GetUsernameAndPassword(args)
  return FirewallAuth(username, password)

if __name__ == "__main__":
  sys.exit(main())
