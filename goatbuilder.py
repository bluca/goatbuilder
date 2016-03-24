#!/usr/bin/env python3
"""
Copyright (c) 2016 Luca Boccassi <luca.boccassi@gmail.com>

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""
import argparse


if __name__ == "__main__":
    with open("/etc/pbuilderrc") as file:
        text = file.read()
    m = re.search(r'PBUILDER_BASE="(.*)"', text)
    if m is not None:
        pbuilderrc = m.group(1)

    parser = argparse.ArgumentParser(description="Automated test for "
                                     "Debian's nvidia-kernel-dkms and "
                                     "nvidia-kernel-source packages via "
                                     "cowbuilder. The tests will be run in "
                                     "parallel per architecture. A valid "
                                     "pbuilderrc is required, and at least a "
                                     "bootstrapped cowbuilder chroot with a"
                                     "name in the format: "
                                     "<TARGET>-<DISTRIBUTION>-<ARCH>")
    parser.add_argument('-p', '--pbuilder-base-path',
                        default=pbuilderrc,
                        help="Path to pbuilder base directory. Defaults to "
                        "value of PBUILDER_BASE in /etc/pbuilderrc.")
    parser.add_argument('-v', '--version', required=True,
                        help='Package version. Required.')

    args = parser.parse_args()
